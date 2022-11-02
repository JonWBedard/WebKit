# Copyright (C) 2022 Apple Inc. All rights reserved.
# Copyright (c) 2006-2008, R Oudkerk. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1.  Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2.  Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3.  Neither the name of author nor the names of any contributors may be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY APPLE INC. AND ITS CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL APPLE INC. OR ITS CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import time
import sys

from webkitcorepy import NullContext

if sys.version_info < (3, 0):
    raise ImportError('Not supported in Python 2')

from multiprocessing import context
from multiprocessing.queues import SimpleQueue, _ForkingPickler

import queue as BaseQueue


class Queue(SimpleQueue):
    Empty = BaseQueue.Empty

    def __init__(self):
        self._closed = False
        super(Queue, self).__init__(ctx=context._default_context)

    def close(self):
        self._closed = True
        self._reader.close()
        self._writer.close()

    def __getstate__(self):
        return super(Queue, self).__getstate__(), self._closed

    def __setstate__(self, state):
        self._closed = state[-1]
        super(Queue, self).__setstate__(state[0])

    def get(self, block=True, timeout=None):
        if self._closed:
            raise ValueError("Queue is closed")
        if block and timeout is None:
            return super(Queue, self).get()

        deadline = (time.monotonic() + timeout) if block else None
        if not self._rlock.acquire(block, timeout):
            raise self.Empty
        try:
            if deadline:
                if not self._poll(deadline - time.monotonic()):
                    raise self.Empty
            elif not self._poll():
                raise self.Empty
            return _ForkingPickler.loads(self._reader.recv_bytes())
        finally:
            self._rlock.release()
