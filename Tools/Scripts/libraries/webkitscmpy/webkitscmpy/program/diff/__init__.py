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

import sys

from webkitcorepy import arguments, Timeout
from webkitscmpy import local

from .diff import DiffBase
from .terminal_diff import TerminalDiff
from .editor_diff import SublimeDiff
from .html_diff import HTMLDiff

from ..command import Command


class Diff(Command):
    name = 'diff'
    help = "Filter 'git diff' output through the user's prefered diff viewer"
    _formats = {}

    @classmethod
    def viewers(cls):
        if not cls._formats:
            cls._formats = {
                differ.name: differ for differ in [
                    TerminalDiff,
                    SublimeDiff,
                    HTMLDiff,
                ] if getattr(differ, 'editor', True)
            }
        return cls._formats

    @classmethod
    def parser(cls, parser, loggers=None):
        parser.add_argument(
            '-b', '--block', '--no-block',
            dest='block', default=False,
            help='Wait for user to stop viewing diff before continuing',
            action=arguments.NoAction,
        )
        parser.add_argument(
            '--include-commit-message', '--no-commit-message',
            dest='commit_message', default=True,
            help='Include (or exclude) commit messages in the provided diff',
            action=arguments.NoAction,
        )
        parser.add_argument(
            '-d', '--differ',
            dest='differ', default=None,
            help='Choose a specific diff viewer ({})'.format(', '.join(sorted(cls.viewers().keys()))),
            type=lambda arg: cls.viewers()[arg],
            choices=cls.viewers().values(),
        )
        parser.add_argument(
            'argument', nargs='?',
            type=str, default=None,
            help='String representation of commit to display diff of',
        )

    @classmethod
    def main(cls, args, repository, **kwargs):
        if not args.differ:
            args.differ = TerminalDiff

        if not args.argument:
            # Check if the user is providing a diff to stdin
            try:
                with Timeout(.1):
                    line = sys.stdin.readline()

                if args.block:
                    sys.stderr.write('Cannot block when receiving diff from stdin\n')

                with args.differ(block=False, repository=repository) as diff_viewer:
                    diff_viewer.add_line(line)
                    diff_viewer.add_file(sys.stdin)
                return 0
            except Timeout.Exception:
                pass

            if not isinstance(repository, local.Git):
                sys.stderr.write("Can only infer local diff in a native Git repository\n")
                return 1

            branch_point = repository.branch_point()
            with args.differ(block=args.block, repository=repository) as diff_viewer:
                diff_viewer.add_lines(repository.diff(
                    head='HEAD',
                    base=branch_point.hash if branch_point else 'HEAD',
                    include_log=args.commit_message,
                ))
            return 0

        head = args.argument
        base = None
        if '..' in args.argument:
            if '...' in args.argument:
                sys.stderr.write("'diff' sub-command only supports '..' notation\n")
                return 1
            references = args.argument.split('..')
            if len(references) > 2:
                sys.stderr.write('Can only include two references in a range\n')
                return 1
            commit_a = repository.find(references[0])
            commit_b = repository.find(references[1])
            head = commit_a.hash if commit_a > commit_b else commit_b.hash
            base = commit_b.hash if commit_a > commit_b else commit_a.hash

        with args.differ(block=args.block, repository=repository) as diff_viewer:
            diff_viewer.add_lines(repository.diff(head=head, base=base, include_log=args.commit_message))

        return 0
