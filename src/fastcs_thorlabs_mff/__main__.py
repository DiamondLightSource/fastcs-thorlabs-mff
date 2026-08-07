from fastcs import launch

from fastcs_thorlabs_mff import __version__
from fastcs_thorlabs_mff.controllers import ThorlabsMFF

launch(controller_classes=ThorlabsMFF, version=__version__)
