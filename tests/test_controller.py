import asyncio

import pytest
import pytest_asyncio
from fastcs.connections import SerialConnectionSettings

from fastcs_thorlabs_mff.controller import ThorlabsMFFController
from fastcs_thorlabs_mff.sim import SimMFFStream


@pytest_asyncio.fixture
async def mff():
    controller = ThorlabsMFFController(SerialConnectionSettings(port="SIM"))
    controller.post_initialise()
    await controller.connect()
    yield controller
    await controller.disconnect()


@pytest.mark.asyncio
async def test_info(mff: ThorlabsMFFController):
    await mff.update_info()
    assert mff.model.get() == "MFF101"
    assert mff.device_type.get() == 0x1007
    assert mff.serial_no.get() == 37000001
    assert mff.firmware_version.get() == 0x010203
    assert mff.hardware_version.get() == 3


@pytest.mark.asyncio
async def test_move_happy_path(mff: ThorlabsMFFController):
    await mff.update_status()
    assert (mff.position.get(), mff.moving.get()) == (False, False)

    await mff.position.put(True)
    seen: list[tuple[bool, bool]] = []
    for _ in range(20):
        await mff.update_status()
        seen.append((mff.position.get(), mff.moving.get()))
        if seen[-1] == (True, False):
            break
        await asyncio.sleep(0.05)

    # Position holds its last confirmed value while moving, then switches once
    assert seen[0] == (False, True)
    assert seen[-1] == (True, False)
    assert set(seen) == {(False, True), (True, False)}

    # The MOVE_COMPLETED sent at the end of the move doesn't upset later reads
    await mff.update_info()
    await mff.update_status()
    assert mff.model.get() == "MFF101"
    assert (mff.position.get(), mff.moving.get()) == (True, False)


@pytest.mark.asyncio
async def test_blink_led(mff: ThorlabsMFFController):
    await mff.blink_led()
    await mff.update_status()
    assert mff.moving.get() is False


@pytest.mark.asyncio
async def test_status_scan_survives_comms_errors(mff: ThorlabsMFFController):
    """A bad reply must not stop fastcs's periodic status scan."""
    _, periodic_scans, _ = mff.create_api_and_tasks()
    scan_task = asyncio.create_task(periodic_scans[0]())
    try:
        await asyncio.sleep(0.3)
        sim = mff.connection.stream
        assert isinstance(sim, SimMFFStream)
        sim.inject(b"\xff")  # stray byte misaligns the next reply
        await asyncio.sleep(0.3)
        await mff.position.put(True)
        for _ in range(40):
            if (mff.position.get(), mff.moving.get()) == (True, False):
                break
            await asyncio.sleep(0.1)
        assert (mff.position.get(), mff.moving.get()) == (True, False)
    finally:
        scan_task.cancel()
