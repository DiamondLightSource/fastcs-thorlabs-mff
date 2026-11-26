import pytest

from fastcs_thorlabs_mff.constants import CHANNEL, DEVICE, HOST, MsgId, StatusBits
from fastcs_thorlabs_mff.messages import APTMessage, Info, Status


@pytest.mark.parametrize(
    "message, expected",
    [
        (APTMessage(MsgId.MOD_IDENTIFY), b"\x23\x02\x00\x00\x50\x01"),
        (APTMessage(MsgId.HW_REQ_INFO), b"\x05\x00\x00\x00\x50\x01"),
        (
            APTMessage(MsgId.MOT_REQ_STATUSBITS, CHANNEL),
            b"\x29\x04\x01\x00\x50\x01",
        ),
        (APTMessage(MsgId.MOT_MOVE_JOG, CHANNEL, 1), b"\x6a\x04\x01\x01\x50\x01"),
        (APTMessage(MsgId.MOT_MOVE_JOG, CHANNEL, 2), b"\x6a\x04\x01\x02\x50\x01"),
    ],
)
def test_commands(message, expected):
    """Encoding of each command the driver sends, against the APT spec."""
    assert message.to_bytes() == expected


@pytest.mark.parametrize(
    "bits, expected",
    [
        (StatusBits.POSITION_1, Status(position=False, moving=False)),
        (StatusBits.POSITION_2, Status(position=True, moving=False)),
        # In transit: neither limit switch, motion bits may or may not be set
        (StatusBits.MOVING_CW, Status(position=None, moving=True)),
        (StatusBits.MOVING_CCW, Status(position=None, moving=True)),
        (0, Status(position=None, moving=True)),
        # Just leaving a limit switch
        (StatusBits.POSITION_1 | StatusBits.MOVING_CCW, Status(False, moving=True)),
        # Unrelated bits are ignored
        (StatusBits.POSITION_2 | 0x0400, Status(position=True, moving=False)),
        # Both limits is nonsense, so position is unknown
        (StatusBits.POSITION_1 | StatusBits.POSITION_2, Status(None, moving=True)),
    ],
)
def test_status_from_data(bits, expected):
    data = (1).to_bytes(2, "little") + int(bits).to_bytes(4, "little")
    assert Status.from_data(data) == expected


def test_info_from_data():
    data = bytearray(84)
    data[0:4] = (37000001).to_bytes(4, "little")
    data[4:12] = b"MFF101\x00\x00"
    data[12:14] = (0x1007).to_bytes(2, "little")
    data[14:18] = (0x010203).to_bytes(4, "little")
    data[78:80] = (3).to_bytes(2, "little")
    assert Info.from_data(bytes(data)) == Info(
        serial_no=37000001,
        model="MFF101",
        device_type=0x1007,
        firmware_version=0x010203,
        hardware_version=3,
    )


@pytest.mark.parametrize(
    "message",
    [
        APTMessage(MsgId.MOT_MOVE_JOG, 1, 2),
        APTMessage(MsgId.HW_GET_INFO, dest=HOST, source=DEVICE, data=bytes(84)),
    ],
)
def test_message_round_trip(message):
    raw = message.to_bytes()
    header, data = raw[:6], raw[6:]
    assert APTMessage.parse_header(header) == (
        message.msg_id,
        message.dest,
        len(message.data),
    )
    assert APTMessage.from_header(header, data) == message
