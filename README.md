[![CI](https://github.com/DiamondLightSource/fastcs-thorlabs-mff/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/fastcs-thorlabs-mff/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/fastcs-thorlabs-mff/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/fastcs-thorlabs-mff)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

# fastcs_thorlabs_mff

FastCS support for Thorlabs motorized filter flip mount

This is where you should write a short paragraph that describes what your module does,
how it does it, and why people should use it.

Source          | <https://github.com/DiamondLightSource/fastcs-thorlabs-mff>
:---:           | :---:
Docker          | `docker run ghcr.io/diamondlightsource/fastcs-thorlabs-mff:latest`
Releases        | <https://github.com/DiamondLightSource/fastcs-thorlabs-mff/releases>

The serial port is configured on the controller's `connection`, either directly with
`port` or from an environment variable with `port_env`:

```yaml
controllers:
  - id: MFF
    type: fastcs_thorlabs_mff.ThorlabsMFF
    connections:
      connection:
        port: "/dev/ttyUSB0"  # or port_env: MFF_PORT
        baud: 115200
transport:
  - epicsca: {}
```

```
python -m fastcs_thorlabs_mff run fastcs.yaml
```

FastCS opens the port, and if the device is unplugged it reopens it, by default
up to 10 times 1 s apart. To run against the simulator, pass `SimMFFConnection`
from Python; it can't be chosen from yaml:

```python
from fastcs.control_system import FastCS
from fastcs.controllers import ControllerSpec
from fastcs.transports.epics.ca import EpicsCATransport

from fastcs_thorlabs_mff.controllers import ThorlabsMFF
from fastcs_thorlabs_mff.sim import SimMFFConnection

FastCS(
    [ControllerSpec("MFF", ThorlabsMFF, connection=SimMFFConnection())],
    [EpicsCATransport()],
).run()
```
