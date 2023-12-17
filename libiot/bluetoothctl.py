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

from . import pexpect
from .pexpect import Alt
from .util import AbortException, Retry
from aridity.config import Config
from diapyr import types
from diapyr.util import innerclass
from functools import partial
import logging, re

log = logging.getLogger(__name__)

def _dataregex(n):
    return ' '.join('[0-9a-f]{2}' for _ in range(n))

def _pathstr(serviceid, charid):
    return f"/service{serviceid:04x}/char{charid:04x}"

set_conn_interval = _pathstr(0x21, 0x45)
temperature_and_humidity = _pathstr(0x21, 0x35)

def _writearg(value):
    def parts(value):
        while value:
            yield f"{value & 0xff:#04x}"
            value >>= 8
    return f'"{" ".join(parts(value))}"'

class BluetoothShell:

    connectok = Alt.plain('Connection successful')
    connectfail = Alt.plain('Failed to connect: org.bluez.Error.Failed')
    notifyfail = Alt.plain('No attribute selected')

    @innerclass
    class Process(pexpect.Process):

        disconnected = Alt.plain('Successful disconnected')

        def __init__(self, label):
            super().__init__('bluetoothctl', self.retry.remaining, f"[{label}] ", self.context)

        def getdata(self, group):
            return bytes.fromhex(self.grouptext(group))

        def disconnect(self, label, cleanup = False):
            log.info("[%s] Disconnect.", label)
            self.print('disconnect')
            return self.disconnected is self.expect(self.disconnected, Alt.plain('Missing device address argument'), cleanup = cleanup)

    def _withprocess(f):
        def g(self, address, *args, **kwargs):
            process = self.Process(address)
            try:
                result = f(process, address, *args, **kwargs)
                log.info("[%s] Done.", address)
                return result
            finally:
                process.dispose()
        return g

    @types(Config, Retry)
    def __init__(self, config, retry):
        self.context = config.context
        self.root = f"/org/bluez/{config.adapter}"
        self.retry = retry

    @_withprocess
    def read_lywsd03mmc(self, address):
        basepath = f"{self.root}/dev_{address.replace(':', '_')}"
        datapath = basepath + temperature_and_humidity
        while True:
            log.info("[%s] Connect.", address)
            self.print(f"connect {address}")
            a = self.expect(self.connectok, self.connectfail, Alt.plain(f"Device {address} not available"))
            if a is self.connectok:
                break
            if a is self.connectfail:
                raise AbortException('Failed to connect.')
            log.info("[%s] Unknown device, try scan.", address)
            self.print('scan on')
            self.expect(Alt.plain(f"Device {address} LYWSD03MMC"))
            self.print('scan off')
        log.info("[%s] Read data.", address)
        self.print('menu gatt', f"select-attribute {basepath}{set_conn_interval}", f"write {_writearg(500)}", f"select-attribute {datapath}", 'notify on')
        if self.notifyfail is self.expect(self.notifyfail, Alt.matchends(f"Attribute {re.escape(datapath)} Value:", f"({_dataregex(5)})")):
            raise AbortException('Disconnected.')
        result = decode_lywsd03mmc(self.getdata(1))
        self.print('back')
        try:
            self.disconnect(address)
        except AbortException:
            log.debug("[%s] Leak connection temporarily.", address)
        return result

    @_withprocess
    def read_h5075(self, address):
        log.info("[%s] Scan.", address)
        self.print('scan on') # FIXME LATER: Allow duplicates somehow.
        self.expect(Alt.matchends(f"Device {re.escape(address)} ManufacturerData Key: 0xec88", f"Device {re.escape(address)} ManufacturerData Value:", f"({_dataregex(6)})"))
        return decode_h5075(self.getdata(1))

    def dispose(self):
        label = 'dispose'
        while True:
            p = self.Process(label)
            try:
                if not p.disconnect(label, True): # FIXME LATER: Do not disconnect from spectator devices.
                    break
            finally:
                p.dispose()

def decode_lywsd03mmc(data):
    val = partial(int.from_bytes, byteorder = 'little')
    return dict(
        temperature = val(data[:2], signed = True) / 100,
        humidity = val(data[2:3]),
        voltage = val(data[3:]) / 1000,
    )

def decode_h5075(data):
    x, y = divmod(int.from_bytes(data[1:4], 'big'), 1000)
    return dict(
        temperature = x / 10,
        humidity = y / 10,
        battery = data[4],
    )
