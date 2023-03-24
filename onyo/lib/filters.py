from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from onyo.lib import Repo


class OnyoInvalidFilterError(Exception):
    """Raise if filters are invalidly defined"""


def asset_name_to_keys(path: Path, default_keys: list[str]) -> dict[str, str]:
    """Convert an asset name to default key values"""
    return dict(zip(default_keys, re.split('[_.]', path.name)))


@dataclass
class Filter:
    _arg: str = field(repr=False)
    repo: Repo = field(repr=False)
    key: str = field(init=False)
    value: str = field(init=False)
    _default_keys: list[str] = field(init=False, default_factory=list)

    def __post_init__(self):
        # TODO: define default keys somewhere accessible _once_
        self._default_keys = ['type', 'make', 'model', 'serial']
        self.key, self.value = self._format(self._arg)

    @staticmethod
    def _format(arg: str) -> list[str]:
        """Split filters by the first occurrence of the `=` (equals) sign."""
        if not isinstance(arg, str) or '=' not in arg:
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')
        return arg.split('=', 1)

    @property
    def is_default(self) -> bool:
        return True if self.key in self._default_keys else False

    @staticmethod
    def _re_match(text: str, r: str) -> bool:
        try:
            return True if re.compile(r).fullmatch(text) else False
        except re.error:
            return False

    def match(self, asset: Path) -> bool:
        """match self on asset contents which must be loaded first"""
        unset = '<unset>'
        string_types = {'<list>': list, '<dict>': dict}

        # filters checking default keys only need to access asset Path
        if self.is_default:
            data = asset_name_to_keys(asset, self._default_keys)
            re_match = self._re_match(str(data[self.key]), self.value)
            if re_match or self.value == data[self.key]:
                return True
            return False

        data = self.repo._read_asset(asset)

        # Check if filter is <unset> and there is no data
        if not data and self.value == unset:
            return True
        elif self.key not in data.keys() and self.value == unset:
            return True
        elif self.key in data.keys() and self.value == unset and (
                data[self.key] is None or data[self.key] == ''):
            return True
        elif self.key not in data.keys() or self.value == unset:
            return False

        # equivalence and regex match
        re_match = self._re_match(str(data[self.key]), self.value)
        if re_match or data[self.key] == self.value:
            return True

        # onyo type representation match
        if self.value in string_types:
            return True if isinstance(
                data[self.key], string_types[self.value]) else False

        return False
