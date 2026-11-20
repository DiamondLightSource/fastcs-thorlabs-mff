"""Thorlabs APT protocol messages used by the MFF101/102 flipper.

Every APT message starts with a 6-byte header:

    bytes 0-1  message ID (little endian)
    bytes 2-3  either two single-byte parameters, or the length of a data packet
               that follows the header (little endian)
    byte  4    destination; the top bit (0x80) is set if a data packet follows
    byte  5    source

See the Thorlabs "APT Communications Protocol" document for details.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag

HEADER_SIZE = 6
HAS_DATA = 0x80
HOST = 0x01
DEVICE = 0x50  # generic USB hardware unit
CHANNEL = 0x01


class MsgId(IntEnum):
    HW_REQ_INFO = 0x0005
    HW_GET_INFO = 0x0006
    MOD_IDENTIFY = 0x0223
    MOT_REQ_STATUSBITS = 0x0429
    MOT_GET_STATUSBITS = 0x042A
    MOT_MOVE_COMPLETED = 0x0464
    MOT_MOVE_JOG = 0x046A


class StatusBits(IntFlag):
    POSITION_1 = 0x01  # CW hardware limit switch
    POSITION_2 = 0x02  # CCW hardware limit switch
    MOVING_CW = 0x10
    MOVING_CCW = 0x20
    JOGGING_CW = 0x40
    JOGGING_CCW = 0x80


MOTION_BITS = (
    StatusBits.MOVING_CW
    | StatusBits.MOVING_CCW
    | StatusBits.JOGGING_CW
    | StatusBits.JOGGING_CCW
)


@dataclass(frozen=True)
class APTMessage:
    msg_id: int
    param1: int = 0
    param2: int = 0
    dest: int = DEVICE
    source: int = HOST
    data: bytes = b""

    @classmethod
    def from_header(cls, header: bytes, data: bytes = b"") -> APTMessage:
        msg_id, param1, param2, dest, source = struct.unpack("<HBBBB", header)
        if data:
            param1 = param2 = 0
        return cls(msg_id, param1, param2, dest & ~HAS_DATA, source, data)

    def to_bytes(self) -> bytes:
        if self.data:
            header = struct.pack(
                "<HHBB", self.msg_id, len(self.data), self.dest | HAS_DATA, self.source
            )
            return header + self.data
        return struct.pack(
            "<HBBBB", self.msg_id, self.param1, self.param2, self.dest, self.source
        )


REPLY_DATA_LENGTHS: dict[int, int] = {
    MsgId.HW_GET_INFO: 84,
    MsgId.MOT_GET_STATUSBITS: 6,
    MsgId.MOT_MOVE_COMPLETED: 14,
}

CHANNEL_REPLIES: set[int] = {MsgId.MOT_GET_STATUSBITS, MsgId.MOT_MOVE_COMPLETED}


def validate_reply(message: APTMessage) -> None:
    """Raise `ValueError` if a known reply has the wrong shape.

    APT has no checksum, so this is what catches a truncated message whose data
    packet has been filled out with the start of the next message.
    """
    expected = REPLY_DATA_LENGTHS.get(message.msg_id)
    if expected is not None and len(message.data) != expected:
        raise ValueError(
            f"0x{message.msg_id:04X} has {len(message.data)} data bytes, "
            f"expected {expected}"
        )
    if message.msg_id in CHANNEL_REPLIES:
        channel = int.from_bytes(message.data[0:2], byteorder="little")
        if channel != CHANNEL:
            raise ValueError(f"0x{message.msg_id:04X} for unexpected channel {channel}")


def data_length(header: bytes) -> int:
    """Length of the data packet following `header`, or 0 if there is none."""
    if header[4] & HAS_DATA:
        return int.from_bytes(header[2:4], byteorder="little")
    return 0


# Host -> device commands


def identify() -> bytes:
    return APTMessage(MsgId.MOD_IDENTIFY).to_bytes()


def req_info() -> bytes:
    return APTMessage(MsgId.HW_REQ_INFO).to_bytes()


def req_status_bits() -> bytes:
    return APTMessage(MsgId.MOT_REQ_STATUSBITS, CHANNEL).to_bytes()


def move_jog(position_2: bool) -> bytes:
    """Move to position 2 if `position_2` is True, otherwise position 1."""
    return APTMessage(MsgId.MOT_MOVE_JOG, CHANNEL, 2 if position_2 else 1).to_bytes()


# Device -> host replies


@dataclass(frozen=True)
class Status:
    position: bool | None
    """True at position 2, False at position 1, None if between the two"""
    moving: bool


def decode_status(data: bytes) -> Status:
    """Decode the data packet of a MOT_GET_STATUSBITS reply."""
    bits = StatusBits(int.from_bytes(data[2:6], byteorder="little") & 0xFF)
    at_1 = StatusBits.POSITION_1 in bits
    at_2 = StatusBits.POSITION_2 in bits
    position = True if at_2 and not at_1 else False if at_1 and not at_2 else None
    moving = bool(bits & MOTION_BITS) or position is None
    return Status(position=position, moving=moving)


@dataclass(frozen=True)
class Info:
    serial_no: int
    model: str
    device_type: int
    firmware_version: int
    hardware_version: int


def decode_info(data: bytes) -> Info:
    """Decode the 84-byte data packet of a HW_GET_INFO reply."""
    return Info(
        serial_no=int.from_bytes(data[0:4], byteorder="little"),
        model=data[4:12].decode("ascii", errors="replace").strip("\x00 "),
        device_type=int.from_bytes(data[12:14], byteorder="little"),
        firmware_version=int.from_bytes(data[14:18], byteorder="little"),
        hardware_version=int.from_bytes(data[78:80], byteorder="little"),
    )
