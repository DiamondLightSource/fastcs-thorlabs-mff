import pytest

from fastcs_thorlabs_mff.protocol import ThorlabsAPTProtocol


@pytest.fixture
def protocol():
    return ThorlabsAPTProtocol()


def test_read_position_false(protocol):
    response = bytearray(12)
    response[8] = 1  # position 1 = False
    assert protocol.read_position(bytes(response)) is False


def test_read_position_true(protocol):
    response = bytearray(12)
    response[8] = 2  # position 2 = True
    assert protocol.read_position(bytes(response)) is True


def test_set_position_true(protocol):
    assert protocol.set_position(True) == b"\x6a\x04\x00\x02\x50\x01"


def test_set_position_false(protocol):
    assert protocol.set_position(False) == b"\x6a\x04\x00\x01\x50\x01"


def test_set_position_roundtrip(protocol):
    for value in (True, False):
        cmd = protocol.set_position(value)
        response = bytearray(12)
        response[8] = cmd[3]  # position byte is at index 3 in command, 8 in response
        assert protocol.read_position(bytes(response)) is value
