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

from Crypto.Cipher import AES
import pkcs7
import base64


class TpLinkCipher:
    def __init__(self, b_arr: bytearray, b_arr2: bytearray):
        self.iv = b_arr2
        self.key = b_arr

    def mime_encoder(to_encode: bytes):
        encoded_list = list(base64.b64encode(to_encode).decode("UTF-8"))

        count = 0
        for i in range(76, len(encoded_list), 76):
            encoded_list.insert(i + count, '\r\n')
            count += 1
        return ''.join(encoded_list)

    def encrypt(self, data):
        data = pkcs7.PKCS7Encoder().encode(data)
        data: str
        cipher = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
        encrypted = cipher.encrypt(data.encode("UTF-8"))
        return TpLinkCipher.mime_encoder(encrypted).replace("\r\n","")

    def decrypt(self, data: str):
        aes = AES.new(bytes(self.key), AES.MODE_CBC, bytes(self.iv))
        pad_text = aes.decrypt(base64.b64decode(data.encode("UTF-8"))).decode("UTF-8")
        return pkcs7.PKCS7Encoder().decode(pad_text)