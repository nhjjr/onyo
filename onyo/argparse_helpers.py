import argparse
import os

from typing import Sequence


class StoreKeyValuePairs(argparse.Action):
    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str,
                 nargs: int | str | None = None,
                 **kwargs) -> None:
        self._nargs = nargs
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 key_values: list[str],
                 option_string: str | None = None) -> None:
        r"""Turn a list of 'key=value' pairs into a list of dictionaries

        Every key appearing multiple times in `key=value` is applied to a new dictionary every time.
        All keys appearing multiple times, must appear the same number of times (and thereby define the number of dicts
        to be created). In case of different counts: raise.
        Every key appearing once in `key_values` will be applied to all dictionaries.
        """

        for kv in key_values:
            if "=" not in kv:
                parser.error(f"Invalid argument '{kv}'. Expected key-value pairs '<key>=<value>'.")
        pairs = [p.split('=', maxsplit=1) for p in key_values]
        register_dict = {k: [] for k, v in pairs}
        [register_dict[k].append(v) for k, v in pairs]
        number_of_dicts = max(len(v) for v in register_dict.values())
        invalid_keys = [(k, len(v)) for k, v in register_dict.items() if 1 < len(v) < number_of_dicts]
        if invalid_keys:
            parser.error(f"All keys given multiple times must be provided the same number of times."
                         f"Max. times a key was given: {number_of_dicts}.{os.linesep}"
                         f"But also got: {', '.join(['{} {} times'.format(k, c) for k, c in invalid_keys])}")

        def cvt(v: str) -> int | float | str | bool:
            if v.lower() == "true":
                return True
            elif v.lower() == "false":
                return False
            try:
                r = int(v)
            except ValueError:
                try:
                    r = float(v)
                except ValueError:
                    r = v
            return r

        results = []
        for i in range(number_of_dicts):
            d = dict()
            for k, values in register_dict.items():
                v = values[0] if len(values) == 1 else values[i]
                d[k] = cvt(v)
            results.append(d)
        setattr(namespace, self.dest, results)
