from __future__ import annotations

import aioserial
from fastcs import ONCE
from fastcs.attributes import AttrR, AttrRW
from fastcs.connections import SerialConnectionSettings
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.logging import logger as _logger
from fastcs.methods import command, scan

from fastcs_thorlabs_mff.connection import READ_TIMEOUT, APTConnection, APTError
from fastcs_thorlabs_mff.constants import CHANNEL, MsgId
from fastcs_thorlabs_mff.io import MFFPositionIO, MFFPositionIORef
from fastcs_thorlabs_mff.messages import APTMessage, Info, Status
from fastcs_thorlabs_mff.sim import SimMFFStream

logger = _logger.bind(logger_name=__name__)


class ThorlabsMFFController(Controller):
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

    def __init__(self, serial_settings: SerialConnectionSettings):
        port, baud = serial_settings.port, serial_settings.baud

        if port.upper() == "SIM":
            logger.info("Using simulated device")
            self.connection = APTConnection(SimMFFStream)
        else:
            logger.info("Using serial port", port=port, baud=baud)
            self.connection = APTConnection(
                lambda: aioserial.AioSerial(
                    port=port, baudrate=baud, timeout=READ_TIMEOUT
                )
            )

        self._status_ok = True
        super().__init__(ios=[MFFPositionIO(self.connection)])

    async def connect(self) -> None:
        logger.info("Connecting to Thorlabs MFF")
        await self.connection.connect()
        await super().connect()

    async def disconnect(self) -> None:
        logger.info("Disconnecting from Thorlabs MFF")
        await self.connection.close()

    @scan(0.2)
    async def update_status(self) -> None:
        try:
            reply = await self.connection.query(
                APTMessage(MsgId.MOT_REQ_STATUSBITS, CHANNEL),
                MsgId.MOT_GET_STATUSBITS,
            )
        except APTError as e:
            if self._status_ok:
                logger.warning("Status query failed, retrying every scan", error=str(e))
                self._status_ok = False
            return
        if not self._status_ok:
            logger.info("Status query succeeded again")
            self._status_ok = True

        status = Status.from_data(reply.data)
        if self.moving.get() and not status.moving:
            logger.info("Move finished", position=2 if status.position else 1)
        await self.moving.update(status.moving)
        if status.position is not None:
            await self.position.update(status.position)

    @scan(ONCE)
    async def update_info(self) -> None:
        reply = await self.connection.query(
            APTMessage(MsgId.HW_REQ_INFO), MsgId.HW_GET_INFO
        )
        info = Info.from_data(reply.data)
        logger.info(
            "Connected to Thorlabs MFF",
            model=info.model,
            serial_no=info.serial_no,
            firmware_version=info.firmware_version,
        )
        await self.model.update(info.model)
        await self.device_type.update(info.device_type)
        await self.serial_no.update(info.serial_no)
        await self.firmware_version.update(info.firmware_version)
        await self.hardware_version.update(info.hardware_version)

    @command()
    async def blink_led(self) -> None:
        logger.info("Blinking LED")
        await self.connection.send(APTMessage(MsgId.MOD_IDENTIFY))
