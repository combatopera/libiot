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

from base64 import b64decode, b64encode
from contextlib import contextmanager
from Crypto.Cipher import AES
from diapyr.util import singleton
from getpass import getpass
from lagoon.util import atomic
from pathlib import Path
from pkcs7 import PKCS7Encoder
import json, logging, os, pickle

log = logging.getLogger(__name__)

class Persistent:

    cacheroot = Path.home() / '.cache' / 'libiot'

    @classmethod
    def loadorcreate(cls, relpath, args, *context):
        try:
            with (cls.cacheroot / relpath).open('rb') as f:
                log.debug("Load cached: %s", relpath)
                obj = pickle.load(f)
                if obj.validate(*context):
                    return obj
        except FileNotFoundError:
            pass
        log.debug("Generate: %s", relpath)
        obj = cls(*args)
        obj.persist(relpath)
        return obj

    def persist(self, relpath):
        with atomic(self.cacheroot / relpath) as p, p.open('wb') as f:
            pickle.dump(self, f)

    def validate(self, *context):
        raise NotImplementedError

class P110Exception(Exception):

    messages = {
        -1501: 'Invalid Request or Credentials',
        -1012: 'Invalid terminalUUID',
        -1010: 'Invalid Public Key Length',
        -1003: 'JSON formatting error',
        -1002: 'Incorrect Request',
    }

    @classmethod
    def check(cls, response):
        errorcode = response['error_code']
        if errorcode:
            raise cls(response, cls.messages.get(errorcode))
        return response.get('result')

    @property
    def error_code(self):
        return self.args[0]['error_code']

def b64str(data):
    return b64encode(data).decode('ascii')

@singleton
class Pad:

    def __init__(self):
        self.encoder = PKCS7Encoder()

    def __getattr__(self, methodname):
        m = getattr(self.encoder, methodname)
        return lambda data: m(data.decode('latin-1')).encode('latin-1')

class Cipher:

    @classmethod
    def create(cls, data):
        return cls(data[:16], data[16:])

    def __init__(self, key, iv):
        self.key = key
        self.iv = iv

    def _aes(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, obj):
        return b64str(self._aes().encrypt(Pad.encode(json.dumps(obj).encode('ascii'))))

    def decrypt(self, text):
        return json.loads(Pad.decode(self._aes().decrypt(b64decode(text))))

@contextmanager
def getpassword(service, username, force):
    os.environ['DBUS_SESSION_BUS_ADDRESS'] = f"unix:path=/run/user/{os.geteuid()}/bus"
    from keyring import get_password, set_password
    password = None if force else get_password(service, username)
    if password is None:
        password = getpass()
        yield password
        set_password(service, username, password)
    else:
        yield password
