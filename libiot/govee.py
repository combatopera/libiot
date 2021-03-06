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

from diapyr.util import innerclass
from bluepy.btle import BTLEDisconnectError, DefaultDelegate, Scanner
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def _deviceindex():
    prefix = 'hci'
    p, = (p for p in Path('/sys/class/bluetooth').iterdir() if p.name.startswith(prefix))
    return int(p.name[len(prefix):])

class Govee:

    class Break(Exception): pass

    @innerclass
    class Delegate(DefaultDelegate):

        result = None

        def handleDiscovery(self, dev, isNewDev, isNewData):
            if dev.addr == self.address:
                data = dev.scanData[255]
                n = int(data[3:6].hex(), 16)
                self.result = dict(
                    temperature = n // 1000 / 10,
                    humidity = n % 1000 / 10,
                    battery = data[6],
                )
                raise self.Break

    def __init__(self, config):
        self.address = config.address.lower()
        self.timeout = config.timeout

    def read(self):
        d = self.Delegate()
        index = _deviceindex()
        s = Scanner(index).withDelegate(d)
        log.info("Scanning device: %s", index)
        try:
            s.scan(self.timeout, passive = True)
        except BTLEDisconnectError as e:
            log.error("Scan error: %s", e)
        except self.Break:
            pass
        return d.result
