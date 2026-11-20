from __future__ import annotations

import logging

from fastcs import ONCE
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command, scan

from fastcs_thorlabs_mff import protocol
from fastcs_thorlabs_mff.config import SerialSettings
from fastcs_thorlabs_mff.connection import APTConnection, serial_stream
from fastcs_thorlabs_mff.io import MFFPositionIO, MFFPositionIORef
from fastcs_thorlabs_mff.protocol import MsgId
from fastcs_thorlabs_mff.sim import SimMFFStream

logger = logging.getLogger(__name__)


class ThorlabsMFF(Controller):
    position = AttrRW(
        Bool(),
        io_ref=MFFPositionIORef(),
        description="False = position 1, True = position 2",
    )
    moving = AttrR(Bool(), description="Moving between positions")
    model = AttrR(String())
    device_type = AttrR(Int())
    serial_no = AttrR(Int())
    firmware_version = AttrR(Int())
    hardware_version = AttrR(Int())

    def __init__(self, serial_settings: SerialSettings):
        self._serial_settings = serial_settings.as_connection_settings()
        port = self._serial_settings.port

        if port.upper() == "SIM":
            logger.info("Using simulated serial connection")
            self.conn = APTConnection(SimMFFStream)
        else:
            logger.info("Using serial connection on port %s", port)
            self.conn = APTConnection(serial_stream(port, self._serial_settings.baud))

        super().__init__(ios=[MFFPositionIO(self.conn)])

    async def connect(self) -> None:
        logger.info("Connecting to Thorlabs MFF")
        await self.conn.connect()
        await super().connect()
        logger.info("Connected to Thorlabs MFF")

    async def disconnect(self) -> None:
        logger.info("Disconnecting from Thorlabs MFF")
        await self.conn.close()

    @scan(0.2)
    async def update_status(self) -> None:
        reply = await self.conn.query(
            protocol.req_status_bits(), MsgId.MOT_GET_STATUSBITS
        )
        status = protocol.decode_status(reply.data)
        await self.moving.update(status.moving)
        if status.position is not None:
            await self.position.update(status.position)

    @scan(ONCE)
    async def update_info(self) -> None:
        reply = await self.conn.query(protocol.req_info(), MsgId.HW_GET_INFO)
        info = protocol.decode_info(reply.data)
        await self.model.update(info.model)
        await self.device_type.update(info.device_type)
        await self.serial_no.update(info.serial_no)
        await self.firmware_version.update(info.firmware_version)
        await self.hardware_version.update(info.hardware_version)

    @command()
    async def blink_led(self) -> None:
        logger.info("Sending blink LED command")
        await self.conn.send(protocol.identify())
