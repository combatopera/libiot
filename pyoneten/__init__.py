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

from .util import b64str, Identity, P110Exception, Cipher
from base64 import b64decode
from hashlib import sha1
from requests import Session
import logging

log = logging.getLogger(__name__)

class P110:

    charset = 'utf-8'
    reqparams = {}

    def __init__ (self, ipAddress, email, password):
        self.identity = Identity() # TODO: Cache this.
        self.session = Session()
        self.url = f"http://{ipAddress}/app"
        self.loginparams = dict(
            username = b64str(sha1(email.encode(self.charset)).hexdigest().encode('ascii')),
            password = b64str(password.encode(self.charset)),
        )

    def _post(self, **kwargs):
        return self.session.post(self.url, params = self.reqparams, json = kwargs, timeout = 10)

    def handshake(self):
        self.cipher = Cipher.create(self.identity.decrypt(b64decode(P110Exception.check(self._post(
            method = 'handshake',
            params = self.identity.handshakepayload(),
        ).json())['key'])))

    def __getattr__(self, methodname):
        def method(**methodparams):
            return P110Exception.check(self.cipher.decrypt(self._post(
                method = 'securePassthrough',
                params = dict(request = self.cipher.encrypt(self.identity.payload(
                    method = methodname,
                    params = methodparams,
                ))),
            ).json()['result']['response']))
        return method

    def login(self):
        self.reqparams = dict(token = self.login_device(**self.loginparams)['token'])

    def ison(self):
        return self.get_device_info()['device_on']

    def on(self):
        self.set_device_info(device_on = True)

    def off(self):
        self.set_device_info(device_on = False)

    def nickname(self):
        return b64decode(self.get_device_info()['nickname']).decode(self.charset)
