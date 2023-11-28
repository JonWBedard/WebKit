# Copyright (C) 2023 Apple Inc. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1.  Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
# 2.  Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
import sys

from webkitcorepy import NullContext, Terminal

from .diff import DiffBase


class TerminalDiff(DiffBase):
    name = 'terminal'

    def __init__(self, **kwargs):
        super(TerminalDiff, self).__init__(**kwargs)
        self._is_conflicting = False

    def add_line(self, line):
        line = super(TerminalDiff, self).add_line(line)
        if not Terminal.isatty(sys.stdout):
            print(line.rstrip())
            return

        add_sub_match = self.ADD_SUB_RE.match(line)
        if add_sub_match:
            parsed_line, _ = line.split(' | ', 1)
            sys.stdout.write('{} | {} '.format(parsed_line, add_sub_match.group(1)))
            if add_sub_match.group(2):
                with Terminal.Style(color=Terminal.Text.green).apply(sys.stdout):
                    sys.stdout.write(add_sub_match.group(2))
            if add_sub_match.group(3):
                with Terminal.Style(color=Terminal.Text.red).apply(sys.stdout):
                    sys.stdout.write(add_sub_match.group(3))
            sys.stdout.write('\n')
            return line

        style = None
        if line.startswith('+<<<'):
            style = Terminal.Style(color=Terminal.Text.magenta)
            self._is_conflicting = True
        elif line.startswith('+===') or line.startswith('+>>>'):
            style = Terminal.Style(color=Terminal.Text.magenta)
            self._is_conflicting = False
        elif line.startswith('diff') or line.startswith('index') or line.startswith('new file') or line.startswith('From') or line.startswith('Date'):
            style = Terminal.Style(color=Terminal.Text.blue)
            self._is_conflicting = False
        elif line.startswith('@@') or line.startswith('---') or line.startswith('+++'):
            style = Terminal.Style(color=Terminal.Text.cyan)
            self._is_conflicting = False
        elif line.startswith('+'):
            style = Terminal.Style(color=Terminal.Text.green)
        elif line.startswith('-') or self._is_conflicting:
            style = Terminal.Style(color=Terminal.Text.red)

        with style.apply(sys.stdout) if style else NullContext():
            sys.stdout.write(line.rstrip())
        sys.stdout.write('\n')
        return line
