"""Numeric constants of the Thorlabs APT protocol used by the MFF101/102 flipper.

See the Thorlabs "APT Communications Protocol" document for details.
"""

from enum import IntEnum, IntFlag

# Header fields
HEADER_SIZE = 6
HAS_DATA = 0x80
"""Set in the destination byte when a data packet follows the header."""
HOST = 0x01
DEVICE = 0x50  # generic USB hardware unit

CHANNEL = 0x01
"""The MFF's only motor channel."""


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

REPLY_DATA_LENGTHS: dict[int, int] = {
    MsgId.HW_GET_INFO: 84,
    MsgId.MOT_GET_STATUSBITS: 6,
    MsgId.MOT_MOVE_COMPLETED: 14,
}
"""Data packet length of each reply the device can send."""

CHANNEL_REPLIES: set[int] = {MsgId.MOT_GET_STATUSBITS, MsgId.MOT_MOVE_COMPLETED}
"""Replies whose data packet starts with a 2-byte channel number."""
