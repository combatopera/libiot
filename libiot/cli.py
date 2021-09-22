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

from .mijia import Delegate
from .p110 import Identity, P110
from .temper import Temper
from .util import getpassword, Retry
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime
from diapyr.util import invokeall
from functools import partial
import json, logging, pytz

log = logging.getLogger(__name__)

def _initlogging():
    logging.basicConfig(format = "%(asctime)s %(levelname)s %(message)s", level = logging.DEBUG)

class CLIP110(P110):

    def status(self):
        return 'on' if self.ison() else 'off'

    def time(self):
        d = self.get_device_time()
        return pytz.utc.localize(datetime.utcfromtimestamp(d['timestamp'])).astimezone(pytz.timezone(d['region'])).strftime('%Y-%m-%d %H:%M:%S %Z')

    def power(self):
        return self.get_energy_usage()['current_power'] / 1000

def main_p110():
    _initlogging()
    config = ConfigCtrl().loadappconfig(main_p110, 'p110.arid')
    parser = ArgumentParser()
    parser.add_argument('-f', action = 'store_true')
    parser.add_argument('--fail', action = 'store_true')
    parser.add_argument('--retry')
    parser.add_argument('command')
    parser.parse_args(namespace = config.cli)
    plugs = dict(-config.plug)
    retry = Retry(config.retry)
    identity = Identity.loadorcreate()
    with ThreadPoolExecutor() as e, ExitStack() as stack, getpassword('p110', config.username, config.force) as password:
        config.cli.password = password
        print(json.dumps(dict(zip(plugs, invokeall([e.submit(retry, partial(config.command, stack.enter_context(P110.loadorcreate(conf, identity)))).result for name, conf in plugs.items()])))))

def main_mijia():
    _initlogging()
    config = ConfigCtrl().loadappconfig(main_mijia, 'mijia.arid')
    parser = ArgumentParser()
    parser.add_argument('--fail', action = 'store_true')
    parser.add_argument('--retry')
    parser.add_argument('path', nargs = '*')
    parser.parse_args(namespace = config.cli)
    sensors = dict(-config.sensor)
    retry = Retry(config.retry)
    with ThreadPoolExecutor() as e:
        print(json.dumps(dict(zip(sensors, invokeall([e.submit(retry, Delegate(conf).read).result for name, conf in sensors.items()])))))

def main_temper():
    _initlogging()
    for t in Temper.discover():
        print(t.read())
