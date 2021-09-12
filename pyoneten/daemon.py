# Copyright 2021 Andrzej Cichocki

# This file is part of pyoneten.
#
# pyoneten is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyoneten is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyoneten.  If not, see <http://www.gnu.org/licenses/>.

# This file incorporates work covered by the following copyright and
# permission notice:

# Copyright 2020 Toby Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from . import P110
from .util import Identity
from aridity.config import ConfigCtrl
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

INADDR_ANY = ''
host = INADDR_ANY
port = 8110

def main_tapod():
    logging.basicConfig(level = logging.DEBUG)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            command = self.path[1:]
            results = [getattr(plug, command)() for plug in plugs]
            self.send_response(200)
            self.end_headers()
            for result in results:
                self.wfile.write(f"{result}\n".encode())
    cc = ConfigCtrl()
    cc.loadsettings()
    config = cc.node.radiator
    identity = Identity.loadorcreate()
    plugs = [P110.loadorcreate(conf, identity) for conf in getattr(config, '0F')]
    HTTPServer((host, port), Handler).serve_forever()
