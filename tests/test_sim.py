import pytest

from fastcs_thorlabs_mff.controllers import ThorlabsMFF
from fastcs_thorlabs_mff.protocol import ThorlabsAPTProtocol
from fastcs_thorlabs_mff.sim import SimMFFConnection

protocol = ThorlabsAPTProtocol()


@pytest.fixture
def sim():
    return SimMFFConnection()


@pytest.mark.asyncio
async def test_initial_position_is_false(sim):
    response = await sim.query_bytes(protocol.get_position(), 12)
    assert protocol.read_position(response) is False


@pytest.mark.asyncio
async def test_set_position_true(sim):
    await sim.write_bytes(protocol.set_position(True))
    response = await sim.query_bytes(protocol.get_position(), 12)
    assert protocol.read_position(response) is True


@pytest.mark.asyncio
async def test_set_position_false(sim):
    await sim.set_position(True)
    await sim.set_position(False)
    assert await sim.get_position() is False


def test_controller_takes_connection(sim):
    controller = ThorlabsMFF(sim)
    assert controller.connection is sim
