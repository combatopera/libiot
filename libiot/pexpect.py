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

from .util import AbortException
from io import BytesIO
from pexpect import EOF, spawn, TIMEOUT
from signal import SIGTERM
from types import SimpleNamespace
import logging, re

log = logging.getLogger(__name__)

class Process:

    def __init__(self, command, remaining, logprefix, context):
        self.buffer = BytesIO()
        self.ctl = spawn(command, logfile = self.buffer)
        self.remaining = remaining
        self.logprefix = logprefix
        self.context = context

    def print(self, *lines):
        for l in lines:
            self.ctl.sendline(l)

    def expect(self, *alternatives, cleanup = False):
        try:
            return alternatives[self.ctl.expect([a.regex for a in alternatives], timeout = None if cleanup else self.remaining())]
        except TIMEOUT:
            log.debug("%sSession tail: %s", self.logprefix, self._tail())
            raise AbortException('Out of time.')

    def _tail(self):
        text = self.buffer.getvalue().decode()
        if not text:
            return text
        lines = text.splitlines(True)
        i = len(lines) - 1
        n = 1
        while n < self.context:
            j = i
            while True:
                j -= 1
                if j < 0 or '\n' == lines[j][-1]:
                    break
            if j < 0:
                break
            i = j
            n += 1
        return ''.join(lines[i:])

    def grouptext(self, group):
        return self.ctl.match.group(group).decode()

    def dispose(self):
        self.ctl.kill(SIGTERM)
        self.expect(SimpleNamespace(regex = EOF), cleanup = True)
        self.ctl.wait()

class Alt:

    @classmethod
    def matchends(cls, *lineends):
        return cls('\r\n[^\n]*'.join(lineends))

    @classmethod
    def plain(cls, text):
        return cls(re.escape(text))

    def __init__(self, regex):
        self.regex = regex
