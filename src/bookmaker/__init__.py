# bookmaker/__init__.py
import sys
from pathlib import Path

print(f'In __init__.py, __package__ = {__package__}')
file = Path('__file__').resolve()

# file.parents[1] should be our packages containing directory, i.e.'src'
print(f'Allow imports to look in {str(file.parents[1])}')

sys.path.append(str(file.parents[1]))
print(f'sys.path = {sys.path}')
# so now we should be able to "from bookmaker import ..."
# since bookmaker will be found in src
print(f'sys.executable = {sys.executable}')

# PyCharm's inspections can't see we have changed sys.path so
# noinspection PyUnresolvedReferences
from bookmaker import about, BookMaker

def main():
    about.main()     # obtain the project's version,
    # either from pyproject.toml during development
    # or using importlib.metadata.version once installed.
    print(f'This is __init__.py in BookMaker version {about.VERSION}')
    BookMaker.main() # enter the application

# Run if called as a script
if __name__ == '__main__':
    print('bookmaker/__init__.py, called as script')
    main()
