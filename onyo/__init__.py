import logging
from onyo._version import __version__
from onyo.lib import (
    Filter, Repo, OnyoInvalidFilterError, OnyoInvalidRepoError,
    OnyoProtectedPathError)


logging.basicConfig(level=logging.ERROR)  # external logging level
log = logging.getLogger('onyo')  # internal logging level
log.setLevel(level=logging.INFO)

__all__ = [
    'log',
    '__version__',
    'Filter',
    'OnyoInvalidFilterError',
    'OnyoInvalidRepoError',
    'OnyoProtectedPathError',
    'Repo']
