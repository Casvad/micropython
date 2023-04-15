from rsa import pkcs1
from rsa import key
import binascii
from network import WLAN
import network
import machine
import time
import json
import http_client


class KangarooService:

    def __init__(self, configuration):
        self.configuration = configuration

    def create_device(self, device_id):
        device_response = http_client.post(self.configuration["host"] + "/devices", json={"mac": device_id},
                                           headers={"Authorization": self.configuration["token"]})

        device_response = device_response
        keys = device_response["keys"]
        jwk_keys = keys["jwk"]

        self.device_id = device_response["device"]["id"]
        self.device_keys = key.PrivateKey.load_pkcs1(bytes(json.dumps(jwk_keys), 'utf-8'))

        device_details = http_client.get(self.configuration["host"] + "/devices/" + self.device_id,
                                         headers={"Authorization": self.configuration["token"]})
        while "digital_twin" not in device_details and device_details["digital_twin"] is None:
            print("Device address is not ready jet")
            time.sleep(1)
            device_details = http_client.get(self.configuration["host"] + "/devices/" + self.device_id,
                                             headers={"Authorization": self.configuration["token"]})

        self.device_address = device_details["digital_twin"]

    def connect_to_internet(self):
        print("Init internet connection")
        wlan = WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.configuration["network_name"], self.configuration["network_password"])
        wlan.isconnected()
        while not wlan.isconnected():
            print("Not connected to internet, retry attempt")
            machine.idle()
            time.sleep(1)
        print("End internet connection")

    def send_message(self, content):
        text_data = json.dumps(content)
        message_signature = pkcs1.sign(text_data, self.device_keys, 'SHA-256')
        json_message = {"device_id": self.device_id,
                        "signature": "0x" + binascii.hexlify(message_signature).decode(),
                        "data": "0x" + binascii.hexlify(text_data).decode()}
        sent = False
        message_response = None
        while not sent:
            try:
                message_response = http_client.post(self.configuration["host"] + "/devices/transaction",
                                                    json=json_message,
                                                    headers={"Authorization": self.configuration["token"]})
                sent = True
            except:
                print("Error calling send message, retry in 1 second")
                time.sleep(1)

        return message_response


def from_configuration(device_id, configuration):
    k = KangarooService(configuration)
    k.connect_to_internet()
    k.create_device(device_id)
    return k
