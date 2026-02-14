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

from aridity.config import Config
from base64 import b64encode
from concurrent.futures import Executor
from Crypto.Cipher import AES
from diapyr import types
from foyndation import innerclass, singleton
from hashlib import sha256
from pkcs7 import PKCS7Encoder
from requests.exceptions import ConnectionError, ReadTimeout
from splut.actor import Spawn
import json, logging, os, time

log = logging.getLogger(__name__)

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

class KLAPCipher:

    @innerclass
    class Channel:

        def __init__(self, seq):
            self.seqbytes = seq.to_bytes(4, 'big', signed = True)
            self.seq = seq

        def _aes(self):
            return AES.new(self.key, AES.MODE_CBC, self.iv + self.seqbytes)

        def encrypt(self, obj):
            ciphertext = self._aes().encrypt(Pad.encode(json.dumps(obj).encode('ascii')))
            return dig(sha256, self.sig + self.seqbytes + ciphertext) + ciphertext

        def decrypt(self, v):
            return json.loads(Pad.decode(self._aes().decrypt(v[32:])))

    def __init__(self, blob):
        self.key = dig(sha256, b'lsk' + blob)[:16]
        ivdata = dig(sha256, b'iv' + blob)
        self.iv = ivdata[:12]
        self.seq = int.from_bytes(ivdata[-4:], 'big', signed = True)
        self.sig = dig(sha256, b'ldk' + blob)[:28]

    def channel(self):
        self.seq = seq = self.seq + 1
        return self.Channel(seq)

def dig(h, v):
    return h(v).digest()

class AbortException(Exception): pass

class Retry:

    abortexceptions = AbortException, ConnectionError, ReadTimeout

    @types(Config)
    def __init__(self, config):
        self.fail = config.retry.fail
        self.giveup = time.time() + float(config.retry.seconds)

    def remaining(self):
        return max(0, self.giveup - time.time())

    def __call__(self, f):
        keepgoing = True
        while keepgoing:
            try:
                return f()
            except self.abortexceptions:
                keepgoing = self.remaining()
                if self.fail and not keepgoing:
                    raise
                log.exception(f"Abort: {f}")

@types(Executor, this = Spawn)
def spawnfactory(e):
    return Spawn(e)

class Worker:

    def run(self, task):
        return task()

@types(Spawn)
def throttlefactory(s):
    return s(*(Worker() for _ in range(os.cpu_count())))
