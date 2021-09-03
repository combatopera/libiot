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

from .util import P110Exception, TpLinkCipher
from base64 import b64decode
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from hashlib import sha1
import json, requests, time, uuid

class P110:

    def __init__ (self, ipAddress, email, password):
        self.terminalUUID = str(uuid.uuid4())
        self.encodedPassword = TpLinkCipher.mime_encoder(password.encode('utf-8'))
        self.encodedEmail = TpLinkCipher.mime_encoder(sha1(email.encode('utf-8')).hexdigest().encode('utf-8'))
        keys = RSA.generate(1024)
        self.privatekey = keys.exportKey('PEM')
        self.publickey  = keys.publickey().exportKey('PEM')
        self.ipAddress = ipAddress

    def handshake(self):
        r = requests.post(f"http://{self.ipAddress}/app", json = dict(
            method = 'handshake',
            params = dict(
                key = self.publickey.decode('utf-8'),
                requestTimeMils = int(round(time.time() * 1000)),
            ),
        ))
        j = r.json()
        do_final = PKCS1_v1_5.new(RSA.importKey(self.privatekey)).decrypt(b64decode(j['result']['key'].encode('utf-8')), None)
        if do_final is None:
            raise ValueError('Decryption failed!')
        self.tpLinkCipher = TpLinkCipher(do_final[:16], do_final[16:])
        try:
            self.headers = dict(Cookie = r.headers['Set-Cookie'][:-13])
        except:
            raise P110Exception(j['error_code'])

    def login(self):
        response = json.loads(self.tpLinkCipher.decrypt(requests.post(f"http://{self.ipAddress}/app", headers = self.headers, json = dict(
            method = 'securePassthrough',
            params = dict(request = self.tpLinkCipher.encrypt(json.dumps(dict(
                method = 'login_device',
                params = dict(
                    username = self.encodedEmail,
                    password = self.encodedPassword,
                ),
                requestTimeMils = int(round(time.time() * 1000)),
            )))),
        )).json()['result']['response']))
        try:
            self.token = response['result']['token']
        except:
            raise P110Exception(response['error_code'])

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
        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))
        SecurePassthroughPayload = {
            "method": "securePassthrough",
            "params": {
                "request": EncryptedPayload
            }
        }
        r = requests.post(URL, json=SecurePassthroughPayload, headers = self.headers)
        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])
        errorcode = json.loads(decryptedResponse)["error_code"]
        if errorcode:
            raise P110Exception(errorcode)

    def setBrightness(self, brightness):
        URL = f"http://{self.ipAddress}/app?token={self.token}"
        Payload = {
            "method": "set_device_info",
            "params":{
                "brightness": brightness
            },
            "requestTimeMils": int(round(time.time() * 1000)),
        }
        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))
        SecurePassthroughPayload = {
            "method": "securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }
        r = requests.post(URL, json=SecurePassthroughPayload, headers = self.headers)
        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])
        errorcode = json.loads(decryptedResponse)["error_code"]
        if errorcode:
            raise P110Exception(errorcode)

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
        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))
        SecurePassthroughPayload = {
            "method": "securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }
        r = requests.post(URL, json=SecurePassthroughPayload, headers = self.headers)
        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])
        errorcode = json.loads(decryptedResponse)["error_code"]
        if errorcode:
            raise P110Exception(errorcode)

    def getDeviceInfo(self):
        URL = f"http://{self.ipAddress}/app?token={self.token}"
        Payload = {
            "method": "get_device_info",
            "requestTimeMils": int(round(time.time() * 1000)),
        }
        EncryptedPayload = self.tpLinkCipher.encrypt(json.dumps(Payload))
        SecurePassthroughPayload = {
            "method":"securePassthrough",
            "params":{
                "request": EncryptedPayload
            }
        }
        r = requests.post(URL, json=SecurePassthroughPayload, headers = self.headers)
        decryptedResponse = self.tpLinkCipher.decrypt(r.json()["result"]["response"])
        return json.loads(decryptedResponse)

    def getDeviceName(self):
        self.handshake()
        self.login()
        data = self.getDeviceInfo()
        data = json.loads(data)
        errorcode = data["error_code"]
        if errorcode:
            raise P110Exception(errorcode)
        encodedName = data["result"]["nickname"]
        name = b64decode(encodedName)
        return name.decode('utf-8')
