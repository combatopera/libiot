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

'Run given command on all configured Shelly plugs.'
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
from foyndation import initlogging
from lagoon.url import URL
import json

class Plugs:

    def __init__(self, config):
        self.urls = {name: URL.binary(f"http://{plug.host}/rpc") for name, plug in -config.plug}

    def _set(self, on):
        print(json.dumps({name: json.loads(url('Switch.Set', query = dict(id = '0', on = on))) for name, url in self.urls.items()}))

    def off(self):
        self._set('false')

    def on(self):
        self._set('true')

    def status(self):
        print(json.dumps({name: json.loads(url('Switch.GetStatus', query = dict(id = '0')))['output'] for name, url in self.urls.items()}))

def main():
    initlogging()
    config = ConfigCtrl().loadappconfig(main, 'shelly.arid')
    parser = ArgumentParser()
    parser.add_argument('command')
    parser.parse_args(namespace = config.cli)
    getattr(Plugs(config), config.command)()

if '__main__' == __name__:
    main()
