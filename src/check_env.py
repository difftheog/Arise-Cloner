"""Environment check used by install.bat and start.bat.

Exits with 0 when Python and every dependency are fine, otherwise prints what
is wrong and exits with 1.
"""
import sys
from importlib import metadata

MIN_PYTHON = (3, 10)

# import name -> pip package it comes from
MODULES = {
    'discord': 'discord.py-self',
    'rich': 'rich',
    'inquirer': 'inquirer',
    'blessed': 'blessed',
    'colorama': 'colorama',
}

# These install into the same `discord` package and break each other.
CONFLICTS = ('discord.py', 'asyncio')


def installed(package: str) -> bool:
    try:
        metadata.version(package)
        return True
    except metadata.PackageNotFoundError:
        return False


def main() -> int:
    problems = []

    if sys.version_info < MIN_PYTHON:
        problems.append('Python %d.%d or newer is required, found %s'
                        % (MIN_PYTHON + (sys.version.split()[0],)))

    for module, package in MODULES.items():
        try:
            __import__(module)
        except ImportError:
            problems.append('missing package: %s' % package)

    for package in CONFLICTS:
        if installed(package):
            problems.append('conflicting package installed: %s' % package)

    if not problems:
        print('Environment OK: Python %s, discord.py-self %s'
              % (sys.version.split()[0], metadata.version('discord.py-self')))
        return 0

    for line in problems:
        print('  - ' + line)
    return 1


if __name__ == '__main__':
    sys.exit(main())
