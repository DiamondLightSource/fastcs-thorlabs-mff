import pytest
import pytest_asyncio

from fastcs_thorlabs_mff import protocol
from fastcs_thorlabs_mff.connection import (
    APTConnection,
    APTFramingError,
    APTTimeoutError,
)
from fastcs_thorlabs_mff.protocol import APTMessage, MsgId
from fastcs_thorlabs_mff.sim import SimMFFStream

STATUS_AT_1 = b"\x01\x00\x01\x00\x00\x00"
MOVE_COMPLETED = APTMessage(
    MsgId.MOT_MOVE_COMPLETED, dest=1, source=0x50, data=b"\x01" + bytes(13)
).to_bytes()


@pytest_asyncio.fixture
async def sim_and_conn():
    sim = SimMFFStream(move_time=0.05, read_timeout=0.05)
    conn = APTConnection(lambda: sim)
    await conn.connect()
    yield sim, conn
    await conn.close()


async def query_status(conn: APTConnection) -> bytes:
    reply = await conn.query(protocol.req_status_bits(), MsgId.MOT_GET_STATUSBITS)
    return reply.data


@pytest.mark.asyncio
async def test_connect_discards_stale_bytes():
    sim = SimMFFStream(read_timeout=0.05)
    sim.inject(b"\x2a\x04\x06")  # partial reply left over from a previous session
    conn = APTConnection(lambda: sim)
    await conn.connect()
    assert await query_status(conn) == STATUS_AT_1


@pytest.mark.parametrize(
    "unsolicited",
    [MOVE_COMPLETED, MOVE_COMPLETED * 3],
    ids=["one", "several"],
)
@pytest.mark.asyncio
async def test_unsolicited_messages_are_skipped(sim_and_conn, unsolicited):
    sim, conn = sim_and_conn
    sim.inject(unsolicited)
    assert await query_status(conn) == STATUS_AT_1
    # and the stream is still aligned for the next query
    assert await query_status(conn) == STATUS_AT_1


@pytest.mark.parametrize(
    "noise, error",
    [
        (b"\xff", APTFramingError),  # stray byte misaligns the header
        # truncated reply, filled out by the start of the next one
        (b"\x2a\x04\x06\x00\x81\x50\x01", APTFramingError),
        (b"\x06\x00\xff\x7f\x81\x50", APTFramingError),  # absurd data length
    ],
    ids=["stray-byte", "truncated", "bad-length"],
)
@pytest.mark.asyncio
async def test_bad_bytes_raise_then_recover(sim_and_conn, noise, error):
    sim, conn = sim_and_conn
    sim.inject(noise)
    with pytest.raises(error):
        await query_status(conn)
    assert await query_status(conn) == STATUS_AT_1


@pytest.mark.parametrize(
    "partial",
    [b"", b"\x2a\x04\x06\x00\x81\x50\x01"],
    ids=["nothing", "truncated"],
)
@pytest.mark.asyncio
async def test_missing_reply_times_out_and_releases_lock(sim_and_conn, partial):
    sim, conn = sim_and_conn
    sim.inject(partial)
    with pytest.raises(APTTimeoutError):
        await conn.query(b"\x00\x00\x00\x00\x50\x01", MsgId.MOT_GET_STATUSBITS)
    assert await query_status(conn) == STATUS_AT_1


@pytest.mark.asyncio
async def test_use_before_connect_raises():
    conn = APTConnection(SimMFFStream)
    with pytest.raises(ConnectionError):
        await conn.send(protocol.identify())
