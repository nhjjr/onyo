import logging
import re
import sys
from collections import Counter
from typing import Generator, Union
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table

from onyo import Filter, Repo, OnyoInvalidRepoError, OnyoInvalidFilterError

logging.basicConfig()
log = logging.getLogger('onyo')


def natural_sort(
        assets: list[tuple[Path, dict[str, str]]],
        keys: Union[list, None] = None, reverse: bool = False) -> list:
    """
    Sort the output of `Repo.get()` by a given list of `keys`.
    """
    if not keys:
        assets = sorted(
            assets,
            key=lambda x: [
                int(s) if s.isdigit() else s.lower()
                for s in re.split('([0-9]+)', str(x[0]))],
            reverse=reverse)
    else:
        for key in reversed(keys):
            assets = sorted(
                assets,
                key=lambda x: [
                    int(s) if s.isdigit() else s.lower() for s in
                    re.split('([0-9]+)', str(x[1][key]))],
                reverse=reverse)

    return assets


def fill_unset(
        assets: Generator[tuple[Path, dict[str, str]], None, None],
        keys: list, unset: str = '<unset>') -> Generator:
    """
    If a key is not present for an asset, define it as `unset` (default is
    `'<unset>'`).
    """
    unset_keys = {key: unset for key in keys}
    for asset, data in assets:
        yield asset, unset_keys | data


def eval_depth(depth: Union[str, int, None], default: int) -> int:
    return int(depth) if depth else default


def eval_filters(
        filters: list[str], repo: Repo, rich: bool = False) -> list[Filter]:
    """Create filters and check if there are no duplicate filter keys"""
    init_filters = []
    try:
        init_filters = [Filter(f, repo=repo) for f in filters]
    except OnyoInvalidFilterError as exc:
        if rich:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {exc}')
        else:
            print(exc, file=sys.stderr)
        exit(1)

    # ensure there are no duplicate filter keys
    dupe = [
        x for x, i in Counter([f.key for f in init_filters]).items() if i > 1]
    if dupe:
        if rich:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] Duplicate filter keys: {dupe}')
        else:
            print(f'Duplicate filter keys: {dupe}', file=sys.stderr)
        exit(1)
    return init_filters


def eval_keys(k: list[str], defaults: list) -> list[str]:
    """Remove duplicates from k and return default keys if k is empty"""
    seen = set()
    k = [x for x in k if not (x in seen or seen.add(x))]
    return k if k else defaults


def eval_path(paths: list[str], defaults: set[str]) -> set[str]:
    """Return the default path if no paths are given"""
    return set(paths) if paths else defaults


def get(args, opdir):
    """
    Display the requested `key`(s) in tabular form for matching assets.
    """
    try:
        repo = Repo(opdir)
    except OnyoInvalidRepoError:
        sys.exit(1)

    # Evaluate and format input
    keys = eval_keys(args.keys, defaults=repo.default_keys)
    paths = eval_path(args.path, defaults={'.'})
    depth = eval_depth(args.depth, default=0)
    filters = eval_filters(
        args.filter, repo=repo, rich=not args.machine_readable)

    results = repo.get(
        keys=set(keys), paths=paths, depth=depth, filters=filters)
    results = fill_unset(results, keys, '<unset>')
    results = natural_sort(
        assets=list(results),
        keys=keys if args.sort_ascending or args.sort_descending else None,
        reverse=True if args.sort_descending else False)

    if args.machine_readable:
        sep = '\t'  # column separator
        for asset, data in results:
            values = f'{sep}'.join([str(value) for value in data.values()])
            print(f'{values}{sep}{asset}')
    else:
        console = Console()
        table = Table(
            box=box.HORIZONTALS, title='', show_header=True,
            header_style='bold')

        for key in keys:
            table.add_column(key, no_wrap=True)

        table.add_column('path', no_wrap=True)

        if results:
            for asset, data in results:
                values = [str(value) for value in data.values()]
                table.add_row(*values, str(asset))

            console.print(table)
        else:
            console.print('No assets matching the filter(s) were found')
