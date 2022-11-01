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
    from multiprocessing import Lock, Pipe

    import Queue as BaseQueue

else:
    from multiprocessing import context
    from multiprocessing.queues import connection, _ForkingPickler

    import queue as BaseQueue

    Lock = context._default_context.Lock
    Pipe = connection.Pipe


# A combination of the multiprocessing module's SimpleQueue from Python 2.7.18 and 3.9.6, but with
# a get() method that support the block and timeout arguments.
class Queue(object):
    Empty = BaseQueue.Empty

    @classmethod
    def time(cls):
        return time.time() if sys.version_info < (3, 0) else time.monotonic()

    def __init__(self):
        self.closed = False
        self._reader, self._writer = Pipe(duplex=False)
        self._rlock = Lock()

        self._poll = self._reader.poll
        if sys.platform == 'win32':
            self._wlock = None
        else:
            self._wlock = Lock()

    def close(self):
        self.closed = True
        self._reader.close()
        self._writer.close()

    def __getstate__(self):
        context.assert_spawning(self)
        return (self._reader, self._writer, self._rlock, self._wlock, self.closed)

    def __setstate__(self, state):
        (self._reader, self._writer, self._rlock, self._wlock, self.closed) = state
        self._poll = self._reader.poll

    def get(self, block=True, timeout=None):
        if self.closed:
            raise ValueError("Queue is closed")
        if block and timeout is None:
            with self._rlock:
                if sys.version_info < (3, 0):
                    return self._reader.recv()
                return _ForkingPickler.loads(self._reader.recv_bytes())

        deadline = (self.time() + timeout) if block else None
        if not self._rlock.acquire(block, timeout):
            raise self.Empty
        try:
            if deadline:
                if not self._poll(deadline - self.time()):
                    raise self.Empty
            elif not self._poll():
                raise self.Empty
            if sys.version_info < (3, 0):
                return self._reader.recv()
            return _ForkingPickler.loads(self._reader.recv_bytes())
        finally:
            self._rlock.release()

    def put(self, obj):
        with self._wlock or NullContext():
            if sys.version_info < (3, 0):
                return self._writer.send(obj)
            return self._writer.send_bytes(_ForkingPickler.dumps(obj))
