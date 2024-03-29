# about.py
#
# Information for presentation in a Help:About dialog.
#
# Some items can be used elsewhere, e.g in __init__.py
# or in setup.cfg

from pathlib import Path
import tomli  # will be import tomllib in Python 3.11

from importlib_metadata import version

NAME = 'BookMaker'
# Single-source the project version from pyproject.toml
VERSION = 'Unknown'
COPYRIGHT = 'Copyright © 2023 Chris Brown and Marcris Software'
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
            pyproject_toml = tomli.load(pyproject_toml_file)
            if 'tool' in pyproject_toml and 'poetry' in pyproject_toml['tool']:
                VERSION = pyproject_toml['tool']['poetry']['version']
                DESCRIPTION = pyproject_toml['tool']['poetry']['description']
    else:
        # ... or using importlib.metadata.version once installed.
        print("Getting version from importlib.metadata")
        VERSION = version("bookmaker-mc")


