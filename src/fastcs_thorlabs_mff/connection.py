"""Send APT messages over a serial stream and read back framed replies.

Replies are read header first, then a data packet of the length given in the header.
Messages that are not the expected reply (e.g. the MOT_MOVE_COMPLETED a device sends
after a move) are discarded. APT has no checksum, so each reply's destination, length
and channel are checked to detect a misaligned stream, and on any error the input
buffer is flushed so the next query starts at a message boundary.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

from fastcs.logging import logger as _logger
from fastcs.tracer import Tracer

from fastcs_thorlabs_mff.constants import (
    CHANNEL,
    CHANNEL_REPLIES,
    HEADER_SIZE,
    HOST,
    REPLY_DATA_LENGTHS,
)
from fastcs_thorlabs_mff.messages import APTMessage

logger = _logger.bind(logger_name=__name__)

READ_TIMEOUT = 0.5
"""Seconds to wait for each read before treating a reply as missing."""

MAX_DISCARDED = 16
"""Unexpected messages to skip while waiting for a reply before giving up."""


class APTError(Exception):
    """A query got no valid reply."""


class Stream(Protocol):
    """The parts of `aioserial.AioSerial` used; a short read means a timeout."""

    async def read_async(self, size: int = 1) -> bytes: ...
    async def write_async(self, data: bytes) -> int | None: ...
    def reset_input_buffer(self) -> None: ...
    def close(self) -> None: ...


class APTConnection(Tracer):
    """APT transactions over the stream returned by `open_stream`, one at a time."""

    stream: Stream

    def __init__(self, open_stream: Callable[[], Stream]):
        super().__init__()
        self._open_stream = open_stream
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self.stream = self._open_stream()
        self.stream.reset_input_buffer()

    async def close(self) -> None:
        async with self._lock:
            self.stream.close()

    async def send(self, message: APTMessage) -> None:
        async with self._lock:
            await self.stream.write_async(message.to_bytes())
            self.log_event("Sent command", command=message.to_bytes().hex(" "))

    async def query(self, message: APTMessage, reply_id: int) -> APTMessage:
        """Send `message` and return the first reply with ID `reply_id`."""
        async with self._lock:
            try:
                await self.stream.write_async(message.to_bytes())
                reply = await self._read_reply(reply_id)
            except APTError:
                self.stream.reset_input_buffer()
                raise
            self.log_event(
                "Received query response",
                query=message.to_bytes().hex(" "),
                response=reply.to_bytes().hex(" "),
            )
            return reply

    async def _read_reply(self, reply_id: int) -> APTMessage:
        for _ in range(MAX_DISCARDED):
            reply = await self._read_message()
            if reply.msg_id == reply_id:
                return reply
            logger.debug(
                "Discarding unexpected message", msg_id=f"0x{reply.msg_id:04X}"
            )
        raise APTError(f"No reply with ID 0x{reply_id:04X} after {MAX_DISCARDED} msgs")

    async def _read_message(self) -> APTMessage:
        """Read one message, raising `APTError` if it is not a well-formed reply."""
        header = await self._read_exact(HEADER_SIZE)
        msg_id, dest, length = APTMessage.parse_header(header)
        if dest != HOST:
            raise APTError(f"Invalid APT header {header.hex(' ')}")

        expected = REPLY_DATA_LENGTHS.get(msg_id, length)
        if length != expected:
            raise APTError(f"0x{msg_id:04X} has {length} data bytes, not {expected}")

        message = APTMessage.from_header(header, await self._read_exact(length))

        # A truncated reply gets filled out with the start of the next message, so
        # its length still looks right but the channel bytes are wrong
        if msg_id in CHANNEL_REPLIES:
            channel = int.from_bytes(message.data[0:2], byteorder="little")
            if channel != CHANNEL:
                raise APTError(f"0x{msg_id:04X} for unexpected channel {channel}")
        return message

    async def _read_exact(self, size: int) -> bytes:
        if size == 0:
            return b""
        data = await self.stream.read_async(size)
        if len(data) < size:
            raise APTError(f"Timed out: expected {size} bytes, got {len(data)}")
        return bytes(data)
