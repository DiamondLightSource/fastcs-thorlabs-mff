from fastcs import launch

from fastcs_thorlabs_mff import __version__
from fastcs_thorlabs_mff.controller import ThorlabsMFFController

launch(controller_classes=ThorlabsMFFController, version=__version__)
