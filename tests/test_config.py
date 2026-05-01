import pytest
from pydantic import ValidationError

from fastcs_thorlabs_mff.config import SerialSettings


def test_port_direct():
    s = SerialSettings(port="/dev/ttyUSB0")
    assert s.port == "/dev/ttyUSB0"


def test_port_env(monkeypatch):
    monkeypatch.setenv("MFF_PORT", "/dev/ttyUSB1")
    s = SerialSettings(port_env="MFF_PORT")
    assert s.port == "/dev/ttyUSB1"


def test_port_env_missing(monkeypatch):
    monkeypatch.delenv("MFF_PORT", raising=False)
    with pytest.raises(ValidationError, match="MFF_PORT"):
        SerialSettings(port_env="MFF_PORT")


def test_port_and_port_env_both_raises():
    with pytest.raises(ValidationError, match="only one"):
        SerialSettings(port="/dev/ttyUSB0", port_env="MFF_PORT")


def test_neither_port_nor_port_env_raises():
    with pytest.raises(ValidationError, match="must be provided"):
        SerialSettings()


def test_baud_default():
    s = SerialSettings(port="/dev/ttyUSB0")
    assert s.baud == 115200


def test_baud_custom():
    s = SerialSettings(port="/dev/ttyUSB0", baud=9600)
    assert s.baud == 9600


def test_as_connection_settings():
    s = SerialSettings(port="/dev/ttyUSB0", baud=9600)
    cs = s.as_connection_settings()
    assert cs.port == "/dev/ttyUSB0"
    assert cs.baud == 9600


def test_sim_port():
    s = SerialSettings(port="SIM")
    assert s.port == "SIM"
