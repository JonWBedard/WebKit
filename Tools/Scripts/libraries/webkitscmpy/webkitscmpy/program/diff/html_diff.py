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

import os
import re
import sys
import tempfile

if sys.version_info >= (3, 2):
    from html import escape
else:
    from cgi import escape

from .diff import DiffBase

from webkitcorepy import Terminal


class HTMLDiff(DiffBase):
    HEAD = '''<html>
<head>
<meta charset='utf-8'>
<style>
:root {
    color-scheme: light dark;
    --border-color: #ddd;
    --background-color: white;
    --border-bottom-color: #998;
    --text-color: #333;
}
@media (prefers-color-scheme: dark) {
    :root {
        --border-color: #444;
        --background-color: black;
        --text-color: #ccc;
    }
    body {
        background-color: var(--background-color);
        color: #eee;
    }
}

.file {
    background-color: #f8f8f8;
    border: 1px solid var(--border-color);
    font-family: monospace;
    margin: 1em 0;
    position: relative;
}
@media (prefers-color-scheme: dark) {
    .file {
        background-color: #212121;
    }
}

h1 {
    color: var(--text-color);
    font-family: sans-serif;
    font-size: 1em;
    margin-left: 0.5em;
    display: inline;
    width: 100%;
    padding: 0.5em;
}

.section {
    background-color: var(--background-color);
    border: solid var(--border-color);
    border-width: 1px 0px;
}

.line, .section-header {
    display: flex;
    white-space: nowrap;
}

.original, .editted {
    border-bottom: 1px solid var(--border-bottom-color);
    border-right: 1px solid var(--border-color);
    color: #444;
    display: inline-block;
    padding: 1px 5px 0px 0px;
    text-align: right;
    vertical-align: bottom;
    width: 3em;
    background-color: #eed;
}
@media (prefers-color-scheme: dark) {
    .original, .editted {
        color: #bbb;
        background-color: #121212;
    }
}

pre, .text {
    padding-left: 5px;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.text {
    white-space: nowrap;
    text-decoration: none;
}
.add {
    background-color: #9e9;
}
.remove {
    background-color: #e99;
}
@media (prefers-color-scheme: dark) {
    .add {
        background-color: #242;
    }
    .remove {
        background-color: #410000;
    }
}

.context {
    border-right: none;
    color: #849;
    background-color: #fef;
    border-bottom: none;
}

@media (prefers-color-scheme: dark) {
    .context {
        color: #a24bb7;
        background-color: #1f0f24;
    }
}
</style>
</head>
<body>
'''
    TAIL = '</body>\n</html>\n'
    INDENT = 4 * ' '
    FILES_CHANGED_RE = re.compile(r'^ (\d+ files? changed)?(create mode\s+)?')
    name = 'html'

    class Type(object):
        DELETED = 0
        MODIFIED = 1
        CREATED = 2
        MOVED = 3

    class Section(object):
        SECTION_RE = re.compile(r'@@\s+-(\d+),\d+\s+\+(\d+),\d+\s+@@\s+(.*)')
        ORIGINAL = 1
        EDITTED = 2
        CONFLICT = 3

        @classmethod
        def from_header(cls, string):
            match = cls.SECTION_RE.match(string)
            if not match:
                return None
            return cls(
                title=match.group(3),
                original_position=match.group(1),
                editted_position=match.group(2),
            )

        def __init__(self, title, original_position, editted_position):
            self.title = title
            self.original_position = int(original_position)
            self.editted_position = int(editted_position)

        def header(self):
            return [
                '<div class="section-header context">',
                '    <span class="original context">@</span>',
                '    <span class="editted context">@</span>',
                '    <span class="section-title">{}</span>'.format(escape(self.title)),
                '</div>',
            ]

        def line(self, line, type=None):
            type_class = {
                self.EDITTED: ' add',
                self.ORIGINAL: ' remove',
                self.CONFLICT: ' context',
            }.get(type, '')
            line_class = {self.CONFLICT: ' context'}.get(type, '')

            result = [
                '<div class="line{}">'.format(type_class),
                '    <span class="original{}">{}</span>'.format(line_class, self.original_position if type in (None, self.ORIGINAL) else ' '),
                '    <span class="editted{}">{}</span>'.format(line_class, self.editted_position if type in (None, self.EDITTED) else ' '),
                '    <span class="text{}">{}</span>'.format(type_class, escape(line)),
                '</div>',
            ]
            if type is not self.EDITTED:
                self.original_position += 1
            if type is not self.ORIGINAL:
                self.editted_position += 1
            return result

    @classmethod
    def title_for(cls, *files):
        files = list(files)
        prefix = ['a/', 'b/']
        for index in range(len(prefix)):
            if not files or len(files) <= index:
                break
            if files[index].startswith(prefix[index]):
                files[index] = files[index][len(prefix[index]):]

        for empty in ['/dev/null']:
            while empty in files or []:
                files.remove(empty)

        if not files:
            return None
        if len(files) == 1:
            return files[0]

        if files[0] == files[1]:
            return files[0]
        return '{} -> {}'.format(*files)

    def commit_message_line(self, line, context=None):
        if context:
            return [
                '<div class="section-header context">',
                '    <span class="original context">{}</span>'.format(escape(context)),
                '    <span class="section-title">{}</span>'.format(escape(line.rstrip())),
                '</div>',
            ]
        result = [
            '<div class="line">',
            '    <span class="original">{}</span>'.format(self._position),
            '    <span class="text">{}</span>'.format(escape(line.rstrip())),
            '</div>',
        ]
        self._position += 1
        return result

    def __init__(self, **kwargs):
        super(HTMLDiff, self).__init__(**kwargs)
        self._file_handle = None
        self._div = []
        self._section = None
        self._current_title = None
        self._files = []
        self._is_conflicting = False
        self._in_commit_message = False
        self._position = 1

        self.file = os.path.join(tempfile.gettempdir(), 'diff.html')

    def _start_div(self, klass=None):
        self._file_handle.write("{}<div class='{}'>\n".format(len(self._div) * self.INDENT, klass))
        self._div.append(klass)

    def _end_div(self, klass=None):
        if not self._div or self._div[-1] != klass:
            return
        self._div.pop()
        self._file_handle.write("{}</div>\n".format(len(self._div) * self.INDENT))

    def add_line(self, line):
        line = super(HTMLDiff, self).add_line(line)
        splitline = line.rstrip().split(maxsplit=1)
        if len(splitline) == 2 and splitline[0] == 'rename':
            splitline = line.rstrip().split(maxsplit=2)
            splitline[0] = '{} {}'.format(splitline[0], splitline.pop(1))
        word = splitline[0] if splitline else None

        if word == '---' and self._in_commit_message:
            self._end_div(klass='file')
            self._in_commit_message = False
            return line

        if self._in_commit_message:
            if word == 'From:' and len(splitline) > 1:
                output_lines = self.commit_message_line(splitline[1], context='By')
            elif word == 'Date:' and len(splitline) > 1:
                output_lines = self.commit_message_line(splitline[1], context='Date')
            else:
                output_lines = self.commit_message_line(line or ' ')
            for output_line in output_lines:
                self._file_handle.write('{}{}\n'.format(len(self._div) * self.INDENT, output_line))
            return line

        if word == 'From':
            self._in_commit_message = True
            self._end_div(klass='file')
            self._start_div(klass='file')
            self._file_handle.write('{}<h1>{}</h1>\n'.format(len(self._div) * self.INDENT, splitline[1] if len(splitline) > 1 else '?'))
            self._start_div(klass='section')
            self._position = 1
            self._section = None
            return line

        if word in ('diff', 'index', 'deleted'):
            self._files = []
            self._end_div(klass='section')
            return line

        if word in ('similarity',):
            return line

        if not self._files and word in ('---', 'rename from') and len(splitline) > 1:
            self._files = [splitline[1]]
            return line
        if len(self._files) == 1 and word in ('+++', 'rename to'):
            self._files.append(splitline[1])
            title = self.title_for(*self._files)

            if title != self._current_title:
                self._end_div(klass='file')
                self._start_div(klass='file')
                self._file_handle.write('{}<h1>{}</h1>\n'.format(len(self._div) * self.INDENT, title))
            self._current_title = title
            return line

        new_section = self.Section.from_header(line)
        if new_section:
            if self._section:
                self._end_div(klass='section')
                self._file_handle.write('{}<br>\n'.format(len(self._div) * self.INDENT))
            self._start_div(klass='section')
            self._is_conflicting = False
            self._section = new_section
            for header_line in self._section.header():
                self._file_handle.write('{}{}\n'.format(len(self._div) * self.INDENT, header_line))
            return line

        if not self._section:
            stripped_line = line.rstrip()
            if not stripped_line:
                return line
            if self.ADD_SUB_RE.match(stripped_line):
                return line
            if self.FILES_CHANGED_RE.match(stripped_line):
                return line

            sys.stderr.write('Unrecognized diff format, excluding:\n')
            sys.stderr.write(line)
            return line

        typ = None
        if line.startswith('+<<<'):
            self._is_conflicting = True
            typ = self._section.CONFLICT
        elif line.startswith('+===') or line.startswith('+>>>'):
            self._is_conflicting = False
            typ = self._section.CONFLICT
        elif line[0] == '-':
            typ = self._section.ORIGINAL
        elif line[0] == '+':
            typ = self._section.EDITTED
        elif self._is_conflicting:
            typ = self._section.ORIGINAL

        for output_line in self._section.line(line[1:-1], type=typ):
            self._file_handle.write('{}{}\n'.format(len(self._div) * self.INDENT, output_line))

        return line

    def __enter__(self):
        self._file_handle = open(self.file, 'w')
        self._div = []
        self._section = None
        self._current_title = None
        self._files = []

        self._file_handle.write(self.HEAD)

        return super(HTMLDiff, self).__enter__()

    def __exit__(self, *args, **kwargs):
        if not self._file_handle:
            return

        while self._div:
            self._end_div(klass=self._div[-1])
        self._file_handle.write(self.TAIL)

        self._file_handle.close()
        self._file_handle = None
        Terminal.open_url('file://{}'.format(self.file))
        return super(HTMLDiff, self).__exit__(*args, **kwargs)
