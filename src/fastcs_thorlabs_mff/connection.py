import logging
import os

from fastcs.connections import SerialConnection

from fastcs_thorlabs_mff.protocol import ThorlabsAPTProtocol

logger = logging.getLogger(__name__)
protocol = ThorlabsAPTProtocol()

POSITION_RESPONSE_SIZE = 12
INFO_RESPONSE_SIZE = 90


def resolve_port(port: str | None, port_env: str | None) -> str:
    """The serial port to open, given directly or by an environment variable.

    Raises:
        ValueError: If both or neither are given, or the variable isn't set

    """
    if port and port_env:
        raise ValueError("Specify only one of 'port' or 'port_env', not both")
    if port_env:
        resolved = os.environ.get(port_env)
        if not resolved:
            raise ValueError(f"Environment variable '{port_env}' is not set")
        logger.info(
            "Resolved port '%s' from environment variable '%s'", resolved, port_env
        )
        return resolved
    if not port:
        raise ValueError("Either 'port' or 'port_env' must be provided")
    return port


class MFFConnection(SerialConnection):
    """Serial link to a Thorlabs MFF, speaking the binary APT protocol.

    The IO methods use `SerialConnection`'s ``write_bytes`` and ``query_bytes``, which
    are already ``@disconnect_on(OSError)``, so a failed or timed out exchange marks the
    link down and FastCS reopens the port.
    """

    def __init__(
        self,
        port: str | None = None,
        port_env: str | None = None,
        baud: int = 115200,
    ):
        super().__init__(port=resolve_port(port, port_env), baud=baud)

    async def get_position(self) -> bool:
        response = await self.query_bytes(
            protocol.get_position(), POSITION_RESPONSE_SIZE
        )
        return protocol.read_position(response)

    async def set_position(self, value: bool) -> None:
        logger.info("Setting position to %s", value)
        await self.write_bytes(protocol.set_position(value))

    async def identify(self) -> None:
        await self.write_bytes(protocol.set_identify())

    async def get_info(self) -> bytes:
        return await self.query_bytes(protocol.get_info(), INFO_RESPONSE_SIZE)

    async def get_model(self) -> str:
        return protocol.read_model(await self.get_info())

    async def get_device_type(self) -> int:
        return protocol.read_type(await self.get_info())

    async def get_serial_no(self) -> int:
        return protocol.read_serial_no(await self.get_info())

    async def get_firmware_version(self) -> int:
        return protocol.read_firmware_v(await self.get_info())

    async def get_hardware_version(self) -> int:
        return protocol.read_hardware_v(await self.get_info())
