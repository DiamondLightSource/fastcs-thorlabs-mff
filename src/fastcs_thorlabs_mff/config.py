import logging
import os

from fastcs.connections import SerialConnectionSettings
from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)


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
                "Resolved port '%s' from environment variable '%s'",
                resolved,
                self.port_env,
            )
            self.port = resolved
        if not self.port:
            raise ValueError("Either 'port' or 'port_env' must be provided")
        return self

    def as_connection_settings(self) -> SerialConnectionSettings:
        assert self.port is not None
        return SerialConnectionSettings(port=self.port, baud=self.baud)


class ControllerConfig(BaseModel):
    serial_settings: SerialSettings


class IOCConfig(BaseModel):
    pv_prefix: str


class GUIConfig(BaseModel):
    output_path: str
    title: str


class TransportConfig(BaseModel):
    ioc: IOCConfig
    gui: GUIConfig


class Config(BaseModel):
    controller: ControllerConfig
    transport: list[TransportConfig]
