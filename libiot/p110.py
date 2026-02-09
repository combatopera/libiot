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

from .util import b64str, dig, KLAPCipher, P110Exception
from aridity.config import Config
from base64 import b64decode
from datetime import datetime
from diapyr import types
from foyndation import null_exc_info
from hashlib import sha1, sha256
from pathlib import Path
from requests import Session
from secrets import token_bytes
from splut.actor import Spawn
import logging, pytz, sys

log = logging.getLogger(__name__)
cachedir = Path('p110')
charset = 'utf-8'

class LoginParams:

    @types(Config)
    def __init__(self, config):
        self.password = config.password
        usernamebytes = config.username.encode(charset)
        passwordbytes = self.password.encode(charset)
        self.params = dict(
            username = b64str(sha1(usernamebytes).hexdigest().encode('ascii')),
            password = b64str(passwordbytes),
        )
        self.hash = dig(sha256, dig(sha1, usernamebytes) + dig(sha1, passwordbytes))

    def dispose(self):
        if null_exc_info == sys.exc_info():
            with self.password:
                pass

class HTTPSession:

    def __init__(self):
        self.s = Session()

    def httppost(self, url, params, data, timeout):
        response = self.s.post(url, params = params, data = data, timeout = timeout)
        response.raise_for_status()
        return response.content

class P110:

    @types(Config, LoginParams, Spawn)
    def __init__(self, config, loginparams, spawn):
        self.host = config.host
        self.timeout = config.timeout
        self.loginparams = loginparams
        self.spawn = spawn

    def ison(self):
        return self.get_device_info()['device_on']

    def on(self):
        self.set_device_info(device_on = True)

    def off(self):
        self.set_device_info(device_on = False)

    def nickname(self):
        return b64decode(self.get_device_info()['nickname']).decode(charset)

    def status(self):
        return 'on' if self.ison() else 'off'

    def time(self):
        d = self.get_device_time()
        return pytz.utc.localize(datetime.utcfromtimestamp(d['timestamp'])).astimezone(pytz.timezone(d['region'])).strftime('%Y-%m-%d %H:%M:%S %Z')

    def power(self):
        return self.get_energy_usage()['current_power'] / 1000

    def _post(self, slug, params, data):
        try:
            session = self.klapsession
        except AttributeError:
            self.klapsession = session = self.spawn(HTTPSession())
        return session.httppost(f"http://{self.host}/app/{slug}", params, data, self.timeout).wait()

    def _handshake(self):
        localtoken = token_bytes(16)
        remotetoken = self._post('handshake1', {}, localtoken)[:16]
        self._post('handshake2', {}, dig(sha256, remotetoken + localtoken + self.loginparams.hash))
        return KLAPCipher(localtoken + remotetoken + self.loginparams.hash)

    def __getattr__(self, methodname):
        if methodname in {'dispose', 'klapsession', 'klapcipher'}:
            raise AttributeError(methodname)
        def method(**methodparams):
            try:
                cipher = self.klapcipher
            except AttributeError:
                self.klapcipher = cipher = self._handshake()
            channel = cipher.channel()
            return P110Exception.check(channel.decrypt(self._post(
                'request',
                dict(seq = channel.seq),
                channel.encrypt(dict(method = methodname, params = methodparams)),
            )))
        return method
