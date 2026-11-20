"""Byte-level simulation of a Thorlabs MFF on a serial port."""

from __future__ import annotations

import asyncio
import logging
import struct

from fastcs_thorlabs_mff.connection import READ_TIMEOUT
from fastcs_thorlabs_mff.protocol import (
    CHANNEL,
    DEVICE,
    HEADER_SIZE,
    HOST,
    APTMessage,
    MsgId,
    StatusBits,
)

logger = logging.getLogger(__name__)

MODEL = b"MFF101\x00\x00"
DEVICE_TYPE = 0x1007
SERIAL_NO = 37000001
FIRMWARE_VERSION = 0x010203
HARDWARE_VERSION = 3


def _reply(msg_id: MsgId, data: bytes) -> bytes:
    return APTMessage(msg_id, dest=HOST, source=DEVICE, data=data).to_bytes()


class SimMFFStream:
    """Stands in for `aioserial.AioSerial` connected to an MFF.

    Moves take `move_time` seconds, during which the status bits report motion and
    neither position, and finish with an unsolicited MOT_MOVE_COMPLETED, as the APT
    protocol specifies for MOT_MOVE_JOG.

    :param move_time: Seconds a move between positions takes
    :param read_timeout: Seconds `read_async` waits before returning a short read
    """

    def __init__(self, move_time: float = 0.5, read_timeout: float = READ_TIMEOUT):
        self.move_time = move_time
        self.read_timeout = read_timeout
        self.position = False  # False = position 1, True = position 2
        self._target: bool | None = None
        self._move_task: asyncio.Task | None = None
        self._rx = bytearray()
        self._rx_changed = asyncio.Event()

    def inject(self, data: bytes) -> None:
        """Queue raw bytes for the host to read, e.g. noise or unsolicited messages"""
        self._rx += data
        self._rx_changed.set()

    async def write_async(self, data: bytes) -> int:
        # Host messages are all header-only
        for i in range(0, len(data) - HEADER_SIZE + 1, HEADER_SIZE):
            self._handle(APTMessage.from_header(data[i : i + HEADER_SIZE]))
        return len(data)

    async def read_async(self, size: int = 1) -> bytes:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.read_timeout
        while len(self._rx) < size and (remaining := deadline - loop.time()) > 0:
            self._rx_changed.clear()
            try:
                await asyncio.wait_for(self._rx_changed.wait(), remaining)
            except TimeoutError:
                break
        data = bytes(self._rx[:size])
        del self._rx[:size]
        return data

    def reset_input_buffer(self) -> None:
        self._rx.clear()

    def close(self) -> None:
        if self._move_task is not None:
            self._move_task.cancel()

    def _handle(self, message: APTMessage) -> None:
        match message.msg_id:
            case MsgId.MOD_IDENTIFY:
                logger.info("[SIM] LED blinking!")
            case MsgId.HW_REQ_INFO:
                self.inject(_reply(MsgId.HW_GET_INFO, self._info()))
            case MsgId.MOT_REQ_STATUSBITS:
                status = struct.pack("<HI", CHANNEL, self._status_bits())
                self.inject(_reply(MsgId.MOT_GET_STATUSBITS, status))
            case MsgId.MOT_MOVE_JOG:
                self._start_move(message.param2 == 2)
            case _:
                logger.warning("[SIM] Ignoring message 0x%04X", message.msg_id)

    def _status_bits(self) -> int:
        if self._target is not None:
            return StatusBits.MOVING_CCW if self._target else StatusBits.MOVING_CW
        return StatusBits.POSITION_2 if self.position else StatusBits.POSITION_1

    def _start_move(self, target: bool) -> None:
        if self._move_task is not None:
            self._move_task.cancel()
        self._target = target
        self._move_task = asyncio.create_task(self._move(target))

    async def _move(self, target: bool) -> None:
        logger.debug("[SIM] Moving to position %d", 2 if target else 1)
        await asyncio.sleep(self.move_time if target != self.position else 0)
        self.position = target
        self._target = None
        # Channel, position, velocity, reserved, status bits
        data = struct.pack("<HiHHI", CHANNEL, 0, 0, 0, self._status_bits())
        self.inject(_reply(MsgId.MOT_MOVE_COMPLETED, data))

    def _info(self) -> bytes:
        data = bytearray(84)
        data[0:4] = SERIAL_NO.to_bytes(4, "little")
        data[4:12] = MODEL
        data[12:14] = DEVICE_TYPE.to_bytes(2, "little")
        data[14:18] = FIRMWARE_VERSION.to_bytes(4, "little")
        data[78:80] = HARDWARE_VERSION.to_bytes(2, "little")
        return bytes(data)
