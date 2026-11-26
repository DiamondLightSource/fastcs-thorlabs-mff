import os

from fastcs.logging import logger as _logger
from pydantic import BaseModel, model_validator

logger = _logger.bind(logger_name=__name__)


class SerialSettings(BaseModel):
    port: str | None = None
    port_env: str | None = None
    baud: int = 115200

    @model_validator(mode="after")
    def resolve_port(self) -> "SerialSettings":
        if self.port and self.port_env:
            raise ValueError("Specify only one of 'port' or 'port_env', not both")
        if self.port_env:
            resolved = os.environ.get(self.port_env)
            if not resolved:
                raise ValueError(f"Environment variable '{self.port_env}' is not set")
            logger.info(
                "Resolved port from environment", port=resolved, env=self.port_env
            )
            self.port = resolved
        if not self.port:
            raise ValueError("Either 'port' or 'port_env' must be provided")
        return self
