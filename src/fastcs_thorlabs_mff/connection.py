"""Message-framed APT connection over a serial stream."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Protocol

import aioserial

from fastcs_thorlabs_mff.protocol import (
    HEADER_SIZE,
    HOST,
    APTMessage,
    data_length,
    validate_reply,
)

logger = logging.getLogger(__name__)

READ_TIMEOUT = 0.5
"""Seconds to wait for each read before treating a reply as missing"""

MAX_DATA_LENGTH = 255
"""Data packets longer than this mean the stream is misaligned"""

MAX_DISCARDED = 16
"""Unexpected messages to skip while waiting for a reply before giving up"""


class APTError(Exception):
    """A query did not get a valid reply"""


class APTTimeoutError(APTError, TimeoutError):
    """No reply, or a truncated one, arrived within the read timeout"""


class APTFramingError(APTError):
    """Bytes that do not form a valid APT header were received"""


class Stream(Protocol):
    """The subset of `aioserial.AioSerial` used by `APTConnection`

    `read_async` must return fewer than `size` bytes if the read times out.
    """

    async def read_async(self, size: int = 1) -> bytes: ...
    async def write_async(self, data: bytes) -> int | None: ...
    def reset_input_buffer(self) -> None: ...
    def close(self) -> None: ...


def serial_stream(port: str, baud: int) -> Callable[[], Stream]:
    def open_stream() -> Stream:
        return aioserial.AioSerial(port=port, baudrate=baud, timeout=READ_TIMEOUT)

    return open_stream


class APTConnection:
    """Send APT commands and read framed replies, one transaction at a time.

    Replies are read header first, then a data packet of the length given in the
    header, and known replies are checked for the right length and channel. Messages
    that are not the expected reply (e.g. the MOT_MOVE_COMPLETED a device sends after a
    move) are discarded. On a timeout or framing error the input buffer is flushed so
    the next query starts at a message boundary.

    :param open_stream: Opens the underlying byte stream on `connect`
    """

    def __init__(self, open_stream: Callable[[], Stream]):
        self._open_stream = open_stream
        self._stream: Stream | None = None
        self._lock = asyncio.Lock()

    @property
    def stream(self) -> Stream:
        if self._stream is None:
            raise ConnectionError("Need to call connect() before using APTConnection")
        return self._stream

    async def connect(self) -> None:
        self._stream = self._open_stream()
        self._stream.reset_input_buffer()

    async def close(self) -> None:
        async with self._lock:
            if self._stream is not None:
                self._stream.close()
                self._stream = None

    async def send(self, message: bytes) -> None:
        async with self._lock:
            await self.stream.write_async(message)

    async def query(self, message: bytes, reply_id: int) -> APTMessage:
        """Send `message` and return the first reply with ID `reply_id`."""
        async with self._lock:
            try:
                await self.stream.write_async(message)
                return await self._read_reply(reply_id)
            except APTError:
                self.stream.reset_input_buffer()
                raise

    async def _read_reply(self, reply_id: int) -> APTMessage:
        for _ in range(MAX_DISCARDED):
            reply = await self._read_message()
            if reply.msg_id == reply_id:
                return reply
            logger.debug("Discarding unexpected APT message 0x%04X", reply.msg_id)
        raise APTError(f"No reply with ID 0x{reply_id:04X} after {MAX_DISCARDED} msgs")

    async def _read_message(self) -> APTMessage:
        header = await self._read_exact(HEADER_SIZE)
        if header[4] & 0x7F != HOST:
            raise APTFramingError(f"Invalid APT header {header.hex(' ')}")
        length = data_length(header)
        if length > MAX_DATA_LENGTH:
            raise APTFramingError(f"Invalid APT data length {length}")
        data = await self._read_exact(length) if length else b""
        message = APTMessage.from_header(header, data)
        try:
            validate_reply(message)
        except ValueError as e:
            raise APTFramingError(str(e)) from e
        return message

    async def _read_exact(self, size: int) -> bytes:
        data = await self.stream.read_async(size)
        if len(data) < size:
            raise APTTimeoutError(f"Expected {size} bytes, got {len(data)}")
        return bytes(data)
