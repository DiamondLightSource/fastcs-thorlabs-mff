import pytest

from fastcs_thorlabs_mff.protocol import ThorlabsAPTProtocol
from fastcs_thorlabs_mff.sim import SimSerialConnection

protocol = ThorlabsAPTProtocol()


@pytest.fixture
def sim():
    return SimSerialConnection()


@pytest.mark.asyncio
async def test_initial_position_is_false(sim):
    response = await sim.send_query(protocol.get_position(), 12)
    assert protocol.read_position(response) is False


@pytest.mark.asyncio
async def test_set_position_true(sim):
    await sim.send_command(protocol.set_position(True))
    response = await sim.send_query(protocol.get_position(), 12)
    assert protocol.read_position(response) is True


@pytest.mark.asyncio
async def test_set_position_false(sim):
    await sim.send_command(protocol.set_position(True))
    await sim.send_command(protocol.set_position(False))
    response = await sim.send_query(protocol.get_position(), 12)
    assert protocol.read_position(response) is False
