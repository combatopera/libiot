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

'Get data from all configured Mijia thermometer/hygrometer 2 sensors.'
from . import initlogging
from ..bluetoothctl import BluetoothShell
from ..util import Retry
from argparse import ArgumentParser
from aridity.config import Config, ConfigCtrl
from concurrent.futures import ThreadPoolExecutor
from diapyr import DI, types
from diapyr.util import invokeall
from functools import partial
import json, logging

class Script:

    @types(Config, BluetoothShell, Retry, ThreadPoolExecutor)
    def __init__(self, config, shell, retry, e):
        self.exclude = set(config.exclude)
        self.sensors = {name: s.address for name, s in -config.sensor}
        self.shell = shell
        self.retry = retry
        self.e = e

    def run(self):
        return dict(zip(self.sensors, invokeall([self.e.submit(self.retry, (lambda: None) if name in self.exclude else partial(self.shell.read_lywsd03mmc, address)).result for name, address in self.sensors.items()])))

def main():
    initlogging()
    config = ConfigCtrl().loadappconfig(main, 'mijia.arid')
    parser = ArgumentParser()
    parser.add_argument('--exclude', action = 'append', default = [])
    parser.add_argument('--fail', action = 'store_true')
    parser.add_argument('--retry')
    parser.add_argument('-v', action = 'store_true')
    parser.parse_args(namespace = config.cli)
    logging.getLogger().setLevel(logging.DEBUG if config.verbose else logging.INFO)
    with DI() as di, ThreadPoolExecutor() as e:
        di.add(BluetoothShell)
        di.add(config)
        di.add(e)
        di.add(Retry)
        di.add(Script)
        print(json.dumps(di(Script).run()))

if '__main__' == __name__:
    main()
