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
from Crypto.Cipher import AES
from pkcs7 import PKCS7Encoder

class P110Exception(Exception):

    messages = {
        -1501: 'Invalid Request or Credentials',
        -1012: 'Invalid terminalUUID',
        -1010: 'Invalid Public Key Length',
        -1003: 'JSON formatting error',
        0: 'Success',
        1002: 'Incorrect Request',
    }

    def __init__(self, errorcode):
        super().__init__(f"Error Code: {errorcode}, {self.messages[errorcode]}")

class TpLinkCipher:

    @staticmethod
    def mime_encoder(to_encode):
        encoded_list = list(b64encode(to_encode).decode('utf-8'))
        count = 0
        for i in range(76, len(encoded_list), 76):
            encoded_list.insert(i + count, '\r\n')
            count += 1
        return ''.join(encoded_list)

    def __init__(self, key, iv):
        self.key = key
        self.iv = iv

    def _aes(self):
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def encrypt(self, data):
        return self.mime_encoder(self._aes().encrypt(PKCS7Encoder().encode(data).encode('utf-8'))).replace('\r\n', '')

    def decrypt(self, data):
        return PKCS7Encoder().decode(self._aes().decrypt(b64decode(data.encode('utf-8'))).decode('utf-8'))
