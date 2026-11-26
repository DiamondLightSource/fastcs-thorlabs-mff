"""Encoding and decoding of APT messages, and of the MFF replies' data packets.

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

from fastcs_thorlabs_mff.constants import (
    DEVICE,
    HAS_DATA,
    HOST,
    MOTION_BITS,
    StatusBits,
)


@dataclass(frozen=True)
class APTMessage:
    msg_id: int
    param1: int = 0
    param2: int = 0
    dest: int = DEVICE
    source: int = HOST
    data: bytes = b""

    @staticmethod
    def parse_header(header: bytes) -> tuple[int, int, int]:
        """Return the message ID, destination and data length (0 if none)."""
        msg_id, length, dest = struct.unpack("<HHB", header[:5])
        if not dest & HAS_DATA:
            length = 0
        return msg_id, dest & ~HAS_DATA, length

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


# Data packets of device -> host replies


@dataclass(frozen=True)
class Status:
    position: bool | None
    """True at position 2, False at position 1, None if between the two."""
    moving: bool

    @classmethod
    def from_data(cls, data: bytes) -> Status:
        """Decode the data packet of a MOT_GET_STATUSBITS reply."""
        bits = StatusBits(int.from_bytes(data[2:6], byteorder="little") & 0xFF)
        at_1 = StatusBits.POSITION_1 in bits
        at_2 = StatusBits.POSITION_2 in bits
        if at_1 == at_2:  # on neither limit switch (or, impossibly, both)
            position = None
        else:
            position = at_2
        moving = bool(bits & MOTION_BITS) or position is None
        return cls(position=position, moving=moving)


@dataclass(frozen=True)
class Info:
    serial_no: int
    model: str
    device_type: int
    firmware_version: int
    hardware_version: int

    @classmethod
    def from_data(cls, data: bytes) -> Info:
        """Decode the 84-byte data packet of a HW_GET_INFO reply."""
        return cls(
            serial_no=int.from_bytes(data[0:4], byteorder="little"),
            model=data[4:12].decode("ascii", errors="replace").strip("\x00 "),
            device_type=int.from_bytes(data[12:14], byteorder="little"),
            firmware_version=int.from_bytes(data[14:18], byteorder="little"),
            hardware_version=int.from_bytes(data[78:80], byteorder="little"),
        )
