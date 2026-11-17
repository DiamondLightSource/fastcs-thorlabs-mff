import pytest

from fastcs_thorlabs_mff.connection import MFFConnection, resolve_port


def test_port_direct():
    assert resolve_port("/dev/ttyUSB0", None) == "/dev/ttyUSB0"


def test_port_env(monkeypatch):
    monkeypatch.setenv("MFF_PORT", "/dev/ttyUSB1")
    assert resolve_port(None, "MFF_PORT") == "/dev/ttyUSB1"


def test_port_env_missing(monkeypatch):
    monkeypatch.delenv("MFF_PORT", raising=False)
    with pytest.raises(ValueError, match="MFF_PORT"):
        resolve_port(None, "MFF_PORT")


def test_port_and_port_env_both_raises():
    with pytest.raises(ValueError, match="only one"):
        resolve_port("/dev/ttyUSB0", "MFF_PORT")


def test_neither_port_nor_port_env_raises():
    with pytest.raises(ValueError, match="must be provided"):
        resolve_port(None, None)


def test_baud_default():
    connection = MFFConnection(port="/dev/ttyUSB0")
    assert connection.baud == 115200


def test_connection_settings():
    connection = MFFConnection(port="/dev/ttyUSB0", baud=9600)
    assert connection.port == "/dev/ttyUSB0"
    assert connection.baud == 9600


def test_connection_port_env(monkeypatch):
    monkeypatch.setenv("MFF_PORT", "/dev/ttyUSB1")
    assert MFFConnection(port_env="MFF_PORT").port == "/dev/ttyUSB1"
