import subprocess
import sys

from fastcs_thorlabs_mff import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "fastcs_thorlabs_mff", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
