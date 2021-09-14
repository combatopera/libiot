# Copyright 2021 Andrzej Cichocki

# This file is part of libiot.
#
# libiot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# libiot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with libiot.  If not, see <http://www.gnu.org/licenses/>.

# This file incorporates work covered by the following copyright and
# permission notice:

# Copyright 2020 Toby Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from .util import b64str, Cipher, P110Exception, Persistent
from base64 import b64decode
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from hashlib import sha1
from pathlib import Path
from requests import Session
from uuid import uuid4
import logging, time

log = logging.getLogger(__name__)
cachedir = Path('p110')

class Identity(Persistent):

    @classmethod
    def loadorcreate(cls):
        return super().loadorcreate(cachedir / 'identity', [])

    def __init__(self):
        key = RSA.generate(1024)
        self.privatekey = key.export_key()
        self.publickey  = key.publickey().export_key().decode('ascii')
        self.terminaluuid = str(uuid4())

    def validate(self):
        return True

    def decrypt(self, data):
        return PKCS1_v1_5.new(RSA.importKey(self.privatekey)).decrypt(data, None)

    def payload(self, **kwargs):
        return dict(
            kwargs,
            requestTimeMils = int(time.time() * 1000),
            terminalUUID = self.terminaluuid,
        )

    def handshakepayload(self):
        return self.payload(key = self.publickey)

class P110(Persistent):

    charset = 'utf-8'

    @classmethod
    def loadorcreate(cls, config, identity):
        return super().loadorcreate(cachedir / config.host, [config, identity], identity)

    def __init__(self, config, identity):
        self.host = config.host
        self.loginparams = dict(
            username = b64str(sha1(config.username.encode(self.charset)).hexdigest().encode('ascii')),
            password = b64str(config.password.encode(self.charset)),
        )
        self.timeout = config.timeout
        self.session = Session()
        self.identity = identity

    def validate(self, contextidentity):
        return self.identity.terminaluuid == contextidentity.terminaluuid

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        if (None, None, None) == exc_info:
            self.persist(cachedir / self.host)

    def _post(self, **kwargs):
        try:
            d = dict(params = self.reqparams)
        except AttributeError:
            d = {}
        return self.session.post(f"http://{self.host}/app", **d, json = kwargs, timeout = self.timeout)

    def _handshake(self):
        self.cipher = Cipher.create(self.identity.decrypt(b64decode(P110Exception.check(self._post(
            method = 'handshake',
            params = self.identity.handshakepayload(),
        ).json())['key'])))

    def __getattr__(self, methodname):
        if methodname.startswith('__') or methodname in {'cipher', 'reqparams'}:
            raise AttributeError(methodname)
        def method(**methodparams):
            while True:
                if not hasattr(self, 'cipher'):
                    self._handshake()
                if not hasattr(self, 'reqparams') and 'login_device' != methodname:
                    self._login()
                try:
                    return P110Exception.check(self.cipher.decrypt(P110Exception.check(self._post(
                        method = 'securePassthrough',
                        params = dict(request = self.cipher.encrypt(self.identity.payload(
                            method = methodname,
                            params = methodparams,
                        ))),
                    ).json())['response']))
                except P110Exception as e:
                    if 9999 != e.error_code:
                        raise
                    for name in 'reqparams', 'cipher':
                        try:
                            delattr(self, name)
                        except AttributeError:
                            pass
                    self.session = Session()
        return method

    def _login(self):
        self.reqparams = dict(token = self.login_device(**self.loginparams)['token'])

    def ison(self):
        return self.get_device_info()['device_on']

    def on(self):
        self.set_device_info(device_on = True)

    def off(self):
        self.set_device_info(device_on = False)

    def nickname(self):
        return b64decode(self.get_device_info()['nickname']).decode(self.charset)
