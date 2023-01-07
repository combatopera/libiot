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

from bluepy.btle import DefaultDelegate, Peripheral
from functools import partial
import logging, math

log = logging.getLogger(__name__)

def carnotcycle(t, rh):
    return 6.112 * math.e ** (17.67 * t / (t + 243.5)) * rh * 2.1674 / (273.15 + t)

def carnotcycle2(t, rh):
    p = 1 - 373.15 / (273.15 + t)
    return 1013.25 * math.e ** (13.3185 * p - 1.9760 * p ** 2 - 0.6445 * p ** 3 - 0.1299 * p ** 4) * rh * 18.01528 / (100 * 0.083145 * (273.15 + t))

def onlineconversion(t, rh):
    return ((0.000002 * t ** 4) + (0.0002 * t ** 3) + (0.0095 * t ** 2) + (0.337 * t) + 4.9034) * rh / 100

def indoorah(t, rh):
    'Diminish effect on measured humidity of absorption at low temperature and evaporation at high temperature.'
    return t / 5 + rh / 10

class Delegate(DefaultDelegate):

    readint = partial(int.from_bytes, byteorder = 'little')

    def __init__(self, config):
        self.address = config.address
        self.path = config.path

    def handleNotification(self, cHandle, data):
        t = self.readint(data[:2], signed = True) / 100
        rh = self.readint(data[2:3])
        self.result = dict(
            temperature = t,
            humidity = rh,
            voltage = self.readint(data[3:]) / 1000,
        )

    def read(self):
        log.info("Connect: %s", self.address)
        p = Peripheral(self.address).withDelegate(self)
        p.writeCharacteristic(0x38, b'\x01\x00')
        p.writeCharacteristic(0x46, b'\xf4\x01\x00')
        log.info('Await notification.')
        while not p.waitForNotifications(1):
            pass
        result = self.result
        for name in self.path:
            result = result[name]
        return result
