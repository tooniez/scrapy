import asyncio

import pytest
from pydispatch import dispatcher
from testfixtures import LogCapture
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from twisted.python.failure import Failure

from scrapy.utils.asyncio import call_later
from scrapy.utils.defer import deferred_from_coro
from scrapy.utils.signal import (
    send_catch_log,
    send_catch_log_async,
    send_catch_log_deferred,
)
from scrapy.utils.test import get_from_asyncio_queue


class TestSendCatchLog:
    @inlineCallbacks
    def test_send_catch_log(self):
        test_signal = object()
        handlers_called = set()

        dispatcher.connect(self.error_handler, signal=test_signal)
        dispatcher.connect(self.ok_handler, signal=test_signal)
        with LogCapture() as log:
            result = yield defer.maybeDeferred(
                self._get_result,
                test_signal,
                arg="test",
                handlers_called=handlers_called,
            )

        assert self.error_handler in handlers_called
        assert self.ok_handler in handlers_called
        assert len(log.records) == 1
        record = log.records[0]
        assert "error_handler" in record.getMessage()
        assert record.levelname == "ERROR"
        assert result[0][0] == self.error_handler  # pylint: disable=comparison-with-callable
        assert isinstance(result[0][1], Failure)
        assert result[1] == (self.ok_handler, "OK")

        dispatcher.disconnect(self.error_handler, signal=test_signal)
        dispatcher.disconnect(self.ok_handler, signal=test_signal)

    def _get_result(self, signal, *a, **kw):
        return send_catch_log(signal, *a, **kw)

    def error_handler(self, arg, handlers_called):
        handlers_called.add(self.error_handler)
        1 / 0

    def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        return "OK"


class TestSendCatchLogDeferred(TestSendCatchLog):
    def _get_result(self, signal, *a, **kw):
        return send_catch_log_deferred(signal, *a, **kw)


class TestSendCatchLogDeferred2(TestSendCatchLogDeferred):
    def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        d = defer.Deferred()
        call_later(0, d.callback, "OK")
        return d


class TestSendCatchLogDeferredAsyncDef(TestSendCatchLogDeferred):
    async def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        await defer.succeed(42)
        return "OK"


@pytest.mark.only_asyncio
class TestSendCatchLogDeferredAsyncio(TestSendCatchLogDeferred):
    async def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        await asyncio.sleep(0.2)
        return await get_from_asyncio_queue("OK")


class TestSendCatchLogAsync(TestSendCatchLog):
    def _get_result(self, signal, *a, **kw):
        return deferred_from_coro(send_catch_log_async(signal, *a, **kw))


class TestSendCatchLogAsync2(TestSendCatchLogAsync):
    def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        d = defer.Deferred()
        call_later(0, d.callback, "OK")
        return d


class TestSendCatchLogAsyncAsyncDef(TestSendCatchLogAsync):
    async def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        await defer.succeed(42)
        return "OK"


@pytest.mark.only_asyncio
class TestSendCatchLogAsyncAsyncio(TestSendCatchLogAsync):
    async def ok_handler(self, arg, handlers_called):
        handlers_called.add(self.ok_handler)
        assert arg == "test"
        await asyncio.sleep(0.2)
        return await get_from_asyncio_queue("OK")


class TestSendCatchLog2:
    def test_error_logged_if_deferred_not_supported(self):
        def test_handler():
            return defer.Deferred()

        test_signal = object()
        dispatcher.connect(test_handler, test_signal)
        with LogCapture() as log:
            send_catch_log(test_signal)
        assert len(log.records) == 1
        assert "Cannot return deferreds from signal handler" in str(log)
        dispatcher.disconnect(test_handler, test_signal)
