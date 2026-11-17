import logging
import os

from fastcs.connections import SerialConnection

logger = logging.getLogger(__name__)


class MFFConnection(SerialConnection):
    """Serial link to a Thorlabs MFF.

    This only adds ``port_env`` to `SerialConnection`, so the port can come from an
    environment variable in yaml. The APT exchanges themselves live on the controller.

    `SerialConnection`'s ``write_bytes`` and ``query_bytes`` are
    ``@disconnect_on(OSError)``, so a failed or timed out exchange marks the link
    down and FastCS reopens the port.
    """

    def __init__(
        self,
        port: str | None = None,
        port_env: str | None = None,
        baud: int = 115200,
    ):
        super().__init__(port=self.resolve_port(port, port_env), baud=baud)

    @staticmethod
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
