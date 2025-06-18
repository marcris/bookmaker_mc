# about.py
#
# Information for presentation in a Help:About dialog.
#
# Some items can be used elsewhere, e.g in __init__.py
# or in setup.cfg

from pathlib import Path

import tomllib  # will be import tomllib in Python 3.11
from importlib_metadata import version

NAME = 'BookMaker'
# Single-source the project version from pyproject.toml
VERSION = 'Version unknown'
COPYRIGHT = 'Copyright © 2025 Chris Brown and Marcris Software'
DESCRIPTION = 'A Book Authoring Application in Python'
AUTHORS = [
    'Chris Brown <chris@marcrisoft.co.uk>'
]
# UPSTART_LOGO = where_am_i() + '/logo.svg'

DEFAULT_LOGO_SIZE_WIDTH = 150
DEFAULT_LOGO_SIZE_HEIGHT = 150

LICENSE_FILE = 'https://opensource.org/licenses/MIT'
# WEBSITE = 'http://www.marcrisoft.co.uk'



def main():
    # obtain the project's version,
    # either from pyproject.toml during development ...
    global VERSION, DESCRIPTION
    pyproject_toml_path = Path('../../pyproject.toml')
    print(f'pyproject_toml_path = {pyproject_toml_path}')
    if pyproject_toml_path.exists():
        print("Getting version from pyproject.toml")
        with open(file=str(pyproject_toml_path), mode='rb') as pyproject_toml_file:
            pyproject_toml = tomllib.load(pyproject_toml_file)
            if 'project' in pyproject_toml:
                VERSION = pyproject_toml['project']['version']
                DESCRIPTION = pyproject_toml['project']['description']
    else:
        # ... or using importlib.metadata.version once installed.
        print("Getting version from importlib.metadata")
        VERSION = 42#version("bookmaker-mc")


