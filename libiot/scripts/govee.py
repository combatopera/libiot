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

'Get data from Govee H5075.'
from . import initlogging
from ..govee import Govee
from argparse import ArgumentParser
from aridity.config import ConfigCtrl
from concurrent.futures import ThreadPoolExecutor
from diapyr.util import invokeall
import json, logging

def main():
    initlogging()
    config = ConfigCtrl().loadappconfig(main, 'govee.arid')
    parser = ArgumentParser()
    parser.add_argument('-v', action = 'store_true')
    parser.parse_args(namespace = config.cli)
    logging.getLogger().setLevel(logging.DEBUG if config.verbose else logging.INFO)
    govees = {name: Govee(s) for name, s in -config.sensor}
    with ThreadPoolExecutor() as e:
        print(json.dumps(dict(zip(govees, invokeall([e.submit(g.read).result for g in govees.values()])))))

if '__main__' == __name__:
    main()
