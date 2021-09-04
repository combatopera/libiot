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

from base64 import b64decode, b64encode
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from pkcs7 import PKCS7Encoder
from uuid import uuid4
import logging

log = logging.getLogger(__name__)

class Identity:

    def __init__(self):
        log.debug('Generate key pair.')
        key = RSA.generate(1024)
        self.privatekey = key.export_key()
        self.publickey  = key.publickey().export_key().decode('ascii')
        self.terminaluuid = str(uuid4())

    def decrypt(self, data):
        return PKCS1_v1_5.new(RSA.importKey(self.privatekey)).decrypt(data, None)

class P110Exception(Exception):

    messages = {
        -1501: 'Invalid Request or Credentials',
        -1012: 'Invalid terminalUUID',
        -1010: 'Invalid Public Key Length',
        -1003: 'JSON formatting error',
        1002: 'Incorrect Request',
    }

    @classmethod
    def check(cls, response):
        errorcode = response['error_code']
        if errorcode:
            raise cls(response, cls.messages.get(errorcode))
        return response

class TpLinkCipher:

    def __init__(self, key, iv):
        self.key = key
        self.iv = iv

    def _aes(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, data):
        return self._aes().encrypt(PKCS7Encoder().encode(data).encode('utf-8'))

    def decrypt(self, data):
        return PKCS7Encoder().decode(self._aes().decrypt(b64decode(data)).decode('utf-8'))
