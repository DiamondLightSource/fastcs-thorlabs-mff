import pytest
import pytest_asyncio

from fastcs_thorlabs_mff.connection import APTConnection, APTError
from fastcs_thorlabs_mff.constants import CHANNEL, DEVICE, HOST, MsgId
from fastcs_thorlabs_mff.messages import APTMessage
from fastcs_thorlabs_mff.sim import SimMFFStream

STATUS_AT_1 = b"\x01\x00\x01\x00\x00\x00"
MOVE_COMPLETED = APTMessage(
    MsgId.MOT_MOVE_COMPLETED, dest=HOST, source=DEVICE, data=b"\x01" + bytes(13)
).to_bytes()


@pytest_asyncio.fixture
async def sim_and_connection():
    sim = SimMFFStream(move_time=0.05, read_timeout=0.05)
    connection = APTConnection(lambda: sim)
    await connection.connect()
    yield sim, connection
    await connection.close()


async def query_status(connection: APTConnection) -> bytes:
    reply = await connection.query(
        APTMessage(MsgId.MOT_REQ_STATUSBITS, CHANNEL),
        MsgId.MOT_GET_STATUSBITS,
    )
    return reply.data


@pytest.mark.asyncio
async def test_connect_discards_stale_bytes():
    sim = SimMFFStream(read_timeout=0.05)
    sim.inject(b"\x2a\x04\x06")  # partial reply left over from a previous session
    connection = APTConnection(lambda: sim)
    await connection.connect()
    assert await query_status(connection) == STATUS_AT_1


@pytest.mark.parametrize(
    "unsolicited",
    [MOVE_COMPLETED, MOVE_COMPLETED * 3],
    ids=["one", "several"],
)
@pytest.mark.asyncio
async def test_unsolicited_messages_are_skipped(sim_and_connection, unsolicited):
    sim, connection = sim_and_connection
    sim.inject(unsolicited)
    assert await query_status(connection) == STATUS_AT_1
    # and the stream is still aligned for the next query
    assert await query_status(connection) == STATUS_AT_1


@pytest.mark.parametrize(
    "noise",
    [
        b"\xff",  # stray byte misaligns the header
        # truncated reply, filled out by the start of the next one
        b"\x2a\x04\x06\x00\x81\x50\x01",
        b"\x06\x00\xff\x7f\x81\x50",  # absurd data length
    ],
    ids=["stray-byte", "truncated", "bad-length"],
)
@pytest.mark.asyncio
async def test_bad_bytes_raise_then_recover(sim_and_connection, noise):
    sim, connection = sim_and_connection
    sim.inject(noise)
    with pytest.raises(APTError):
        await query_status(connection)
    assert await query_status(connection) == STATUS_AT_1


@pytest.mark.parametrize(
    "partial",
    [b"", b"\x2a\x04\x06\x00\x81\x50\x01"],
    ids=["nothing", "truncated"],
)
@pytest.mark.asyncio
async def test_missing_reply_times_out_and_releases_lock(sim_and_connection, partial):
    sim, connection = sim_and_connection
    sim.inject(partial)
    with pytest.raises(APTError, match="Timed out"):
        await connection.query(APTMessage(0), MsgId.MOT_GET_STATUSBITS)  # no reply
    assert await query_status(connection) == STATUS_AT_1


@pytest.mark.asyncio
async def test_use_before_connect_raises():
    connection = APTConnection(SimMFFStream)
    with pytest.raises(ConnectionError):
        await connection.send(APTMessage(MsgId.MOD_IDENTIFY))
