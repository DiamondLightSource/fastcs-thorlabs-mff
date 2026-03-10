import fastcs

from fastcs_thorlabs_mff.controllers import (
    ThorlabsMFF,
)

from . import __version__

__all__ = ["main"]


def main() -> None:
    fastcs.launch(ThorlabsMFF, version=__version__)


if __name__ == "__main__":
    main()
