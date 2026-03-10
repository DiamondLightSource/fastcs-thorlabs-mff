from __future__ import annotations

from dataclasses import dataclass

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

protocol = ThorlabsAPTProtocol()


@dataclass
class ThorlabsMFFSettings:
    serial_settings: SerialConnectionSettings


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

    def __init__(self, settings: ThorlabsMFFSettings):
        super().__init__(ios=[MFFAttributeIO(self)])
        self.suffix = ""
        self._settings = settings

        if settings.serial_settings.port.upper() == "SIM":
            self.conn = SimSerialConnection()
        else:
            self.conn = SerialConnection()

    async def connect(self) -> None:
        await self.conn.connect(self._settings.serial_settings)

    async def disconnect(self) -> None:
        await self.conn.close()

    @command()
    async def toggle_position(self) -> None:
        current_position = self.position.get()
        await self.conn.send_command(protocol.set_position(not current_position))

    @command()
    async def blink_led(self) -> None:
        await self.conn.send_command(protocol.set_identify())
