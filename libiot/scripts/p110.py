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

'Run given command on all configured Tapo P100/P110 plugs.'
from . import initlogging
from ..p110 import Identity, LoginParams, P110
from ..util import Retry
from argparse import ArgumentParser
from aridity.config import Config, ConfigCtrl
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from diapyr import DI, types
from diapyr.util import invokeall
import json, logging

@types(this = Identity)
def identityfactory():
    return Identity.loadorcreate()

@types(Config, Identity, LoginParams, this = P110)
def p110factory(config, identity, loginparams):
    return P110.loadorcreate(config, identity).Client(config, loginparams)

class Command:

    @types(Config, Retry, P110, str)
    def __init__(self, config, retry, p110, name):
        self.command = getattr(p110, config.command)
        self.retry = retry
        self.name = name

    def __call__(self):
        return self.name, self.retry(self.command)

def main():
    initlogging()
    config = ConfigCtrl().loadappconfig(main, 'p110.arid')
    parser = ArgumentParser()
    parser.add_argument('--cron', action = 'store_true')
    parser.add_argument('-f', action = 'store_true')
    parser.add_argument('--fail', action = 'store_true')
    parser.add_argument('--retry')
    parser.add_argument('-v', action = 'store_true')
    parser.add_argument('command')
    parser.parse_args(namespace = config.cli)
    logging.getLogger().setLevel(logging.DEBUG if config.verbose else logging.INFO)
    with DI() as di, ExitStack() as stack, ThreadPoolExecutor() as e:
        di.add(config)
        di.add(identityfactory)
        di.add(Retry)
        di.add(LoginParams)
        def entryfuture(name, conf):
            plugdi = stack.enter_context(DI(di))
            plugdi.add(name)
            plugdi.add(conf)
            plugdi.add(p110factory)
            plugdi.add(Command)
            return e.submit(plugdi(Command))
        print(json.dumps(dict(invokeall([entryfuture(*item).result for item in -config.plug]))))

if '__main__' == __name__:
    main()
