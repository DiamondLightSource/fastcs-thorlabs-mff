from __future__ import annotations

import logging

from fastcs.attributes import AttrR, AttrRW
from fastcs.connections import (
    SerialConnection,
    SerialConnectionSettings,
)
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Int, String
from fastcs.methods import command

from fastcs_thorlabs_mff.io import MFFAttributeIO, MFFAttributeIORef
from fastcs_thorlabs_mff.protocol import ThorlabsAPTProtocol
from fastcs_thorlabs_mff.sim import SimSerialConnection

logger = logging.getLogger(__name__)
protocol = ThorlabsAPTProtocol()


class ThorlabsMFF(Controller):
    position = AttrRW(
        Bool(),
        io_ref=MFFAttributeIORef(
            name="position",
            response_handler=protocol.read_position,
            response_size=12,
            read_cmd=protocol.get_position,
            write_cmd=protocol.set_position,
            update_period=0.2,
        ),
    )
    model = AttrR(
        String(),
        io_ref=MFFAttributeIORef(
            name="model",
            response_handler=protocol.read_model,
            response_size=90,
            read_cmd=protocol.get_info,
        ),
    )
    device_type = AttrR(
        Int(),
        io_ref=MFFAttributeIORef(
            name="device_type",
            response_handler=protocol.read_type,
            response_size=90,
            read_cmd=protocol.get_info,
        ),
    )
    serial_no = AttrR(
        Int(),
        io_ref=MFFAttributeIORef(
            name="serial_no",
            response_handler=protocol.read_serial_no,
            response_size=90,
            read_cmd=protocol.get_info,
        ),
    )
    firmware_version = AttrR(
        Int(),
        io_ref=MFFAttributeIORef(
            name="firmware_version",
            response_handler=protocol.read_firmware_v,
            response_size=90,
            read_cmd=protocol.get_info,
        ),
    )
    hardware_version = AttrR(
        Int(),
        io_ref=MFFAttributeIORef(
            name="hardware_version",
            response_handler=protocol.read_hardware_v,
            response_size=90,
            read_cmd=protocol.get_info,
        ),
    )

    def __init__(self, serial_settings: SerialConnectionSettings):
        self._serial_settings = serial_settings

        if self._serial_settings.port.upper() == "SIM":
            logger.info("Using simulated serial connection")
            self.conn = SimSerialConnection()
        else:
            logger.info("Using serial connection on port %s", serial_settings.port)
            self.conn = SerialConnection()

        super().__init__(ios=[MFFAttributeIO(self)])

    async def connect(self) -> None:
        logger.info("Connecting to Thorlabs MFF")
        await self.conn.connect(self._serial_settings)
        await super().connect()
        logger.info("Connected to Thorlabs MFF")

    async def disconnect(self) -> None:
        logger.info("Disconnecting from Thorlabs MFF")
        await self.conn.close()

    @command()
    async def blink_led(self) -> None:
        logger.info("Sending blink LED command")
        await self.conn.send_command(protocol.set_identify())
