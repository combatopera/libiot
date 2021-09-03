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
from uuid import uuid4
import json, requests, time

class P110:

    reqparams = {}

    def __init__ (self, ipAddress, email, password):
        self.terminalUUID = str(uuid4())
        self.loginparams = dict(
            username = TpLinkCipher.mime_encoder(sha1(email.encode('utf-8')).hexdigest().encode('utf-8')),
            password = TpLinkCipher.mime_encoder(password.encode('utf-8')),
        )
        keys = RSA.generate(1024)
        self.privatekey = keys.exportKey('PEM')
        self.publickey  = keys.publickey().exportKey('PEM')
        self.url = f"http://{ipAddress}/app"

    def handshake(self):
        r = requests.post(self.url, json = dict(
            method = 'handshake',
            params = dict(
                key = self.publickey.decode('utf-8'),
                requestTimeMils = int(time.time() * 1000),
            ),
        ))
        self.headers = dict(Cookie = r.headers['Set-Cookie'][:-13])
        response = P110Exception.check(r.json())
        do_final = PKCS1_v1_5.new(RSA.importKey(self.privatekey)).decrypt(b64decode(response['result']['key']), None)
        if do_final is None:
            raise ValueError('Decryption failed!')
        self.tpLinkCipher = TpLinkCipher(do_final[:16], do_final[16:])

    def __getattr__(self, methodname):
        def m(**params):
            return P110Exception.check(json.loads(self.tpLinkCipher.decrypt(requests.post(self.url, headers = self.headers, params = self.reqparams, json = dict(
                method = 'securePassthrough',
                params = dict(request = self.tpLinkCipher.encrypt(json.dumps(dict(
                    method = methodname,
                    params = params,
                    requestTimeMils = int(time.time() * 1000),
                    terminalUUID = self.terminalUUID,
                )))),
            )).json()['result']['response'])))
        return m

    def login(self):
        self.reqparams = dict(token = self.login_device(**self.loginparams)['result']['token'])

    def turnOn(self):
        self.set_device_info(device_on = True)

    def turnOff(self):
        self.set_device_info(device_on = False)

    def setBrightness(self, brightness):
        self.set_device_info(brightness = brightness)

    def getDeviceInfo(self):
        return self.get_device_info()

    def getDeviceName(self):
        return b64decode(self.get_device_info()['result']['nickname']).decode('utf-8')
