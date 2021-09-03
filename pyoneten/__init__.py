# Copyright 2021 Andrzej Cichocki

# This file is part of pyoneten.
#
# pyoneten is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyoneten is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyoneten.  If not, see <http://www.gnu.org/licenses/>.

# This file incorporates work covered by the following copyright and
# permission notice:

# Copyright 2020 Toby Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from .tp_link_cipher import TpLinkCipher
from .util import errorcodes
from base64 import b64decode, b64encode
from Crypto.Cipher import AES, PKCS1_OAEP, PKCS1_v1_5
from Crypto.PublicKey import RSA
import ast, hashlib, json, pkgutil, requests, time, uuid

class P110:

    def __init__ (self, ipAddress, email, password):
        self.ipAddress = ipAddress
        self.terminalUUID = str(uuid.uuid4())

        self.email = email
        self.password = password
        self.encryptCredentials(email, password)
        self.createKeyPair()

    def encryptCredentials(self, email, password):
        #Password Encoding
        self.encodedPassword = TpLinkCipher.mime_encoder(password.encode("utf-8"))

        #Email Encoding
        self.encodedEmail = self.sha_digest_username(email)
        self.encodedEmail = TpLinkCipher.mime_encoder(self.encodedEmail.encode("utf-8"))

    def createKeyPair(self):
        self.keys = RSA.generate(1024)

        self.privateKey = self.keys.exportKey("PEM")
        self.publicKey  = self.keys.publickey().exportKey("PEM")

    def decode_handshake_key(self, key):
        decode: bytes = b64decode(key.encode("UTF-8"))
        decode2: bytes = self.privateKey

        cipher = PKCS1_v1_5.new(RSA.importKey(decode2))
        do_final = cipher.decrypt(decode, None)
        if do_final is None:
            raise ValueError("Decryption failed!")

        b_arr:bytearray = bytearray()
        b_arr2:bytearray = bytearray()

        for i in range(0, 16):
            b_arr.insert(i, do_final[i])
        for i in range(0, 16):
            b_arr2.insert(i, do_final[i + 16])

        return TpLinkCipher(b_arr, b_arr2)

    def sha_digest_username(self, data):
        b_arr = data.encode("UTF-8")
        digest = hashlib.sha1(b_arr).digest()

        sb = ""
        for i in range(0, len(digest)):
            b = digest[i]
            hex_string = hex(b & 255).replace("0x", "")
            if len(hex_string) == 1:
                sb += "0"
                sb += hex_string
            else:
                sb += hex_string

        return sb

    def handshake(self):
        URL = f"http://{self.ipAddress}/app"
        Payload = {
            "method":"handshake",
            "params":{
                "key": self.publicKey.decode("utf-8"),
                "requestTimeMils": int(round(time.time() * 1000))
            }
        }

        r = requests.post(URL, json=Payload)

        encryptedKey = r.json()["result"]["key"]
        self.tpLinkCipher = self.decode_handshake_key(encryptedKey)

        try:
            self.cookie = r.headers["Set-Cookie"][:-13]

        except:
            errorCode = r.json()["error_code"]
            errorMessage = errorcodes[str(errorCode)]
            raise Exception(f"Error Code: {errorCode}, {errorMessage}")

    def login(self):
        URL = f"http://{self.ipAddress}/app"
        Payload = {
            "method":"login_device",
            "params":{
                "username": self.encodedEmail,
                "password": self.encodedPassword
            },
            "requestTimeMils": int(round(time.time() * 1000)),
        }
        headers = {
            "Cookie": self.cookie
        }

        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))

        SecurePassthroughPayload = {
            "method":"securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }

        r = requests.post(URL, json=SecurePassthroughPayload, headers=headers)

        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])

        try:
            self.token = ast.literal_eval(decryptedResponse)["result"]["token"]
        except:
            errorCode = ast.literal_eval(decryptedResponse)["error_code"]
            errorMessage = errorcodes[str(errorCode)]
            raise Exception(f"Error Code: {errorCode}, {errorMessage}")

    def turnOn(self):
        URL = f"http://{self.ipAddress}/app?token={self.token}"
        Payload = {
            "method": "set_device_info",
            "params":{
                "device_on": True
            },
            "requestTimeMils": int(round(time.time() * 1000)),
            "terminalUUID": self.terminalUUID
        }

        headers = {
            "Cookie": self.cookie
        }

        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))

        SecurePassthroughPayload = {
            "method": "securePassthrough",
            "params": {
                "request": EncryptedPayload
            }
        }

        r = requests.post(URL, json=SecurePassthroughPayload, headers=headers)

        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])

        if ast.literal_eval(decryptedResponse)["error_code"] != 0:
            errorCode = ast.literal_eval(decryptedResponse)["error_code"]
            errorMessage = errorcodes[str(errorCode)]
            raise Exception(f"Error Code: {errorCode}, {errorMessage}")

    def setBrightness(self, brightness):
        URL = f"http://{self.ipAddress}/app?token={self.token}"
        Payload = {
            "method": "set_device_info",
            "params":{
                "brightness": brightness
            },
            "requestTimeMils": int(round(time.time() * 1000)),
        }

        headers = {
            "Cookie": self.cookie
        }

        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))

        SecurePassthroughPayload = {
            "method": "securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }

        r = requests.post(URL, json=SecurePassthroughPayload, headers=headers)

        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])

        if ast.literal_eval(decryptedResponse)["error_code"] != 0:
            errorCode = ast.literal_eval(decryptedResponse)["error_code"]
            errorMessage = errorcodes[str(errorCode)]
            raise Exception(f"Error Code: {errorCode}, {errorMessage}")

    def turnOff(self):
        URL = f"http://{self.ipAddress}/app?token={self.token}"
        Payload = {
            "method": "set_device_info",
            "params":{
                "device_on": False
            },
            "requestTimeMils": int(round(time.time() * 1000)),
            "terminalUUID": self.terminalUUID
        }

        headers = {
            "Cookie": self.cookie
        }

        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))

        SecurePassthroughPayload = {
            "method": "securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }

        r = requests.post(URL, json=SecurePassthroughPayload, headers=headers)

        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])

        if ast.literal_eval(decryptedResponse)["error_code"] != 0:
            errorCode = ast.literal_eval(decryptedResponse)["error_code"]
            errorMessage = errorcodes[str(errorCode)]
            raise Exception(f"Error Code: {errorCode}, {errorMessage}")

    def getDeviceInfo(self):
        URL = f"http://{self.ipAddress}/app?token={self.token}"
        Payload = {
            "method": "get_device_info",
            "requestTimeMils": int(round(time.time() * 1000)),
        }

        headers = {
            "Cookie": self.cookie
        }

        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))

        SecurePassthroughPayload = {
            "method":"securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }

        r = requests.post(URL, json=SecurePassthroughPayload, headers=headers)
        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])

        return json.loads(decryptedResponse)

    def getDeviceName(self):
        self.handshake()
        self.login()
        data = self.getDeviceInfo()

        data = json.loads(data)

        if data["error_code"] != 0:
            errorCode = ast.literal_eval(decryptedResponse)["error_code"]
            errorMessage = errorcodes[str(errorCode)]
            raise Exception(f"Error Code: {errorCode}, {errorMessage}")
        else:
            encodedName = data["result"]["nickname"]
            name = b64decode(encodedName)
            return name.decode("utf-8")
