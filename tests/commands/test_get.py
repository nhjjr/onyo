import re
import subprocess
from pathlib import Path
from typing import Any, Generator, Union

from onyo.commands.get import (
    natural_sort, fill_unset, eval_depth, eval_filters, eval_keys, eval_path)
from onyo.lib import Repo, Filter
import pytest


def convert_contents(
        raw_assets: list[tuple[str, dict[str, Any]]]) -> Generator:
    """Convert content dictionary to a plain-text string"""
    for file, raw_contents in raw_assets:
        contents = ''
        for k, v in raw_contents.items():
            if isinstance(v, str):
                v = f"'{v}'"
            elif isinstance(v, bool):
                v = str(v).lower()
            contents += f'{k}: {v}\n'
        yield [file, contents]


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('one/laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('one/two/headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'}),
    ('abc/def/monitor_dell_pro.4', {'str': 'foo=bar'})]))
@pytest.mark.parametrize('filters', [['str=bar', 'type=laptop'], []])
@pytest.mark.parametrize('depth', ['0', '1', '2'])
@pytest.mark.parametrize('keys', [
    [], ['make', 'serial'], ['num', 'str', 'bool']])
@pytest.mark.parametrize('paths', [['.'], ['one/two', 'abc/def']])
@pytest.mark.parametrize('machine_readable', ['-H', None])
@pytest.mark.parametrize('sort', ['-s', None])
def test_get_all(
        repo: Repo, filters: list[str], depth: str, keys: list[str],
        paths: list[str], machine_readable: Union[str, None],
        sort: Union[str, None]) -> None:
    """
    Test `onyo get` with a combination of arguments.
    """
    keys = keys if keys else repo.pseudo_keys
    cmd = [
        'onyo', 'get', '--filter', *filters, '--keys', *keys,
        '--path', *paths, '--depth', depth]
    cmd += [machine_readable] if machine_readable else []
    cmd += [sort] if sort else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]
    init_paths = set(Path(path) for path in paths)

    if machine_readable:
        for line in output:
            # match filters
            for f in filters:
                key, value = f.split('=', 1)
                if key in keys:  # we cannot test unrequested keys
                    assert line[keys.index(key)] == value

            # match depth
            n_parents = len(Path(line[-1]).parents) - 1
            assert n_parents <= int(depth)
            assert len(line) == len(keys) + 1  # +1 to include path

            if init_paths:
                assert any(init_paths & set(Path(line[-1]).parents))

    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('one/laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('one/two/headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'}),
    ('monitor_dell_pro.4', {'str': 'foo=bar'})]))
@pytest.mark.parametrize('filters_expected', [
    (['type=laptop'], 2),
    (['str=bar', 'type=laptop'], 1),
    (['make=apple', 'str=bar'], 1),
    (['bool=True'], 2),
    (['bool=False'], 1),
    (['num=8'], 2),
    (['num=16'], 1),
    (['unset=foo'], 0),
    (['str=foo', 'unset=bar'], 0),
    (['str=foo=bar'], 1),
    ([], 4)])
def test_get_filter(
        repo: Repo, filters_expected: tuple[list[str], int]) -> None:
    """
    Test that `onyo get --filter KEY=VALUE --depth 999` retrieves the expected
    files.

    Parametrized filters contain Tuple([filters], n_assets expected to match).
    """
    filters, n_assets = filters_expected
    keys = repo.pseudo_keys + ['num', 'str', 'bool', 'unset']
    cmd = [
        'onyo', 'get', '--filter', *filters, '--depth', '999', '--keys', *keys,
        '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # assert that all values match the filters
    for key in filters:
        key, value = key.split('=', 1)
        for line in output:
            assert line[keys.index(key)] == value

    assert len(output) == n_assets
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo'}),
    ('one/laptop_dell_precision.2', {'num': '16', 'str': 'foobar'}),
    ('one/two/headphones_apple_pro.3', {'num': '8GB', 'str': 'bar'}),
    ('one/two/headphones_dell_pro.4', {'num': '10GB', 'str': 'bar'})]))
@pytest.mark.parametrize('filters_expected', [
    (['type=lap'], 0),  # full-matches only
    (['type=lap.*'], 2),
    (['num=8.*'], 2),
    (['str=foo.*'], 2),
    ([r'num=9\d*|\d{1,}'], 2)])
def test_get_filter_regex(
        repo: Repo, filters_expected: tuple[list[str], int]) -> None:
    """
    Test that `onyo get --filter KEY=VALUE --depth 999` retrieves the expected
    files.

    Parametrized filters contain Tuple([filters], n_assets expected to match).
    """
    filters, n_assets = filters_expected
    keys = repo.pseudo_keys + ['num', 'str', 'bool', 'unset']
    cmd = [
        'onyo', 'get', '--filter', *filters, '--depth', '999', '--keys', *keys,
        '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # assert that all values match the filters
    for key in filters:
        key, value = key.split('=', 1)
        r = re.compile(value)

        for line in output:
            assert r.match(line[keys.index(key)])

    assert len(output) == n_assets
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('one/laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('one/two/headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'})]))
@pytest.mark.parametrize('filters', [
    ['type=laptop', 'type=laptop'],
    ['type=laptop', 'type=headphones'],
    ['num=16', 'num=16'],
    ['num=8', 'num=16'],
    ['num=8.*', 'num=16.*'],
    ['num']])
def test_get_filter_errors(repo: Repo, filters: list[str]) -> None:
    """
    Test that `onyo get --filter KEY=VALUE --depth 999` retrieves the expected
    files.

    Parametrized filters contain Tuple([filters], n_assets expected to match).
    """
    cmd = ['onyo', 'get', '--filter', *filters, '--depth', '999', '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)

    assert ret.stderr
    assert not ret.stdout
    assert ret.returncode == 1


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('one/laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('one/two/headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'})]))
@pytest.mark.parametrize('keys', [
    ['type', 'make', 'model', 'serial'],
    ['unset', 'type', 'unset2', 'make'],
    ['num', 'str', 'bool'],
    ['TyPe', 'MAKE', 'moDEL', 'NuM', 'STR'],
    []])
def test_get_keys(repo: Repo, keys: list) -> None:
    """
    Test that `onyo get --depth 3 --keys x y z` retrieves the expected keys.
    """
    raw_assets = [
        ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
        ('one/laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
        ('one/two/headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'})]

    cmd = ['onyo', 'get', '--depth', '999', '--keys', *keys, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # default keys returned if no keys were specified
    if not keys:
        keys = repo.pseudo_keys

    # Get all the key values and make sure they match
    for line in output:
        asset = raw_assets[[a[0] for a in raw_assets].index(line[-1])][1]

        # add type, make, model, serial from asset name
        asset = asset | dict(zip(
            ['type', 'make', 'model', 'serial'],
            re.split('[_.]', Path(line[-1]).name)))

        for i, key in enumerate(keys):
            # convert raw asset values to str because output type is str
            assert str(asset.get(key, '<unset>')) == line[i]

    assert len(output) == len(repo.assets)
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {}),
    ('one/laptop_dell_precision.2', {}),
    ('one/two/headphones_apple_pro.3', {}),
    ('one/two/three/headphones_apple_pro.4', {}),
    ('one/two/three/four/headphones_apple_pro.5', {})]))
@pytest.mark.parametrize('depth_expected', [
    ('0', 1), ('1', 2), ('2', 3), ('3', 4), ('4', 5), ('999', 5), ('-1', 0)])
def test_get_depth(repo: Repo, depth_expected: tuple[str, int]) -> None:
    """
    Test that `onyo get --depth x` retrieves the expected assets.

    Parametrized depth contains Tuple(depth, n_assets expected to match).
    """
    depth, n_assets = depth_expected
    cmd = ['onyo', 'get', '--depth', depth, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # Ensure all listed assets have a path equal to or smaller than depth
    for line in output:
        # . is returned if 0 parents, hence `- 1`
        n_parents = len(Path(line[-1]).parents) - 1
        assert n_parents <= int(depth)

    assert len(output) == n_assets
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {}),
    ('one/laptop_dell_precision.2', {}),
    ('one/two/headphones_apple_pro.3', {}),
    ('one/two/three/headphones_apple_pro.4', {}),
    ('one/two/three/four/headphones_apple_pro.5', {}),
    ('another/dir/headphones_apple_pro.5', {})]))
@pytest.mark.parametrize('paths_expected', [
    (['./one'], 4),
    (['./one/two'], 3),
    (['./one/two/three'], 2),
    (['one/two/three'], 2),
    (['/one/two/three'], 0),
    (['./one/two/three/four'], 1),
    (['./path/that/does/not/exist/but/is/very/long'], 0),
    (['/path/that/does/not/exist/and/does/not/start/with/dot'], 0),
    (['path/that/does/not/exist/and/does/not/start/with/dot/or/slash'], 0),
    (['.', './one', './one/two/three/four'], 6),
    (['./one/two/three/four', './another/dir'], 2),
    (['def/ghi'], 0),
    ([], 6)])
def test_get_paths(repo: Repo, paths_expected: tuple[str, int]) -> None:
    """
    Test that `onyo get --path x` retrieves the expected assets.

    Parametrized path contains Tuple([paths], n_assets expected to match).
    """
    paths, n_assets = paths_expected
    cmd = ['onyo', 'get', '--depth', '999', '--path', *paths, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # Ensure one of the given paths matches the outermost parents of each asset
    paths = set(Path(path) for path in paths)

    if paths:
        for line in output:
            assert any(paths & set(Path(line[-1]).parents))

    assert len(output) == n_assets
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('a13bc_foo_bar.1', {'num': 'num-3'}),
    ('a2cd_foo_bar.2', {'num': 'num-16'}),
    ('a36ab_foo_bar.3', {'num': 'num-20'})]))
@pytest.mark.parametrize('sort', ['-s', '-S', ''])
@pytest.mark.parametrize('keys', [
    ['type'], ['num'], ['unset', 'type'], []])
def test_get_sort(repo: Repo, sort: str, keys: list[str]) -> None:
    """
    Test that `onyo get --keys x y z` with `-s` (ascending) or `-S`
    (descending)  retrieves assets in the expected 'natural sorted' order.
    """
    presorted = {
        'path': ['a2cd_foo_bar.2', 'a13bc_foo_bar.1', 'a36ab_foo_bar.3'],
        'type': ['a2cd', 'a13bc', 'a36ab'],
        'num': ['num-3', 'num-16', 'num-20']}

    cmd = ['onyo', 'get', '--depth', '999', '--keys', *keys, '-H']
    cmd = cmd + [sort] if sort else cmd
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    for index, key in enumerate(keys or ['type']):
        key, index = (key, index) if sort in ['-s', '-S'] else ('path', -1)
        sorted_values = presorted.get(key, ['<unset>'] * 3)
        print(key)
        values = [line[index] for line in output]

        if sort == '-S':
            sorted_values = list(reversed(sorted_values))

        assert values == sorted_values

    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.parametrize('keys', [None, ['num'], ['str', 'num']])
@pytest.mark.parametrize('reverse', [True, False])
def test_natural_sort(
        keys: Union[list, None], reverse: bool) -> None:
    assets = [
        (Path('a13bc_foo_bar.1'), {'num': 'num-20', 'str': 'abc', 'id': '1'}),
        (Path('a2cd_foo_bar.2'), {'num': 'num-3', 'str': 'def', 'id': '2'}),
        (Path('a36ab_foo_bar.3'), {'num': 'num-16', 'str': 'ghi', 'id': '3'})]
    sorted_assets = natural_sort(assets, keys=keys, reverse=reverse)
    ids = [data.get('id') for _, data in sorted_assets]

    if reverse:
        ids = list(reversed(ids))

    if keys is None:
        assert ids == ['2', '1', '3']
    elif keys[0] == 'num':
        assert ids == ['2', '3', '1']
    elif keys[0] == 'str':
        assert ids == ['1', '2', '3']


def test_fill_unset() -> None:
    assets = [
        (Path('a13bc_foo_bar.1'), {'num': 'num-20', 'str': 'abc'}),
        (Path('a2cd_foo_bar.2'), {'num': 'num-3'}),
        (Path('a36ab_foo_bar.3'), {'str': 'ghi'})]
    keys = ['type', 'make', 'model', 'serial', 'num', 'str', 'id']
    filled = list(fill_unset((a for a in assets), keys=keys))

    for i, (asset, data) in enumerate(filled):
        assert isinstance(asset, Path)
        assert asset == assets[i][0]
        for k, v in data.items():
            assert v == assets[i][1].get(k, '<unset>')

    assert filled[1][1]['str'] == '<unset>'
    assert filled[2][1]['num'] == '<unset>'


@pytest.mark.parametrize('depth', [None, '2', 2])
def test_eval_depth(depth: Union[str, int, None]) -> None:
    assert eval_depth(depth, default=2) == 2


@pytest.mark.parametrize('filters', [
    ['type=laptop'], ['type=laptop', 'make=foo', 'bar=1']])
def test_eval_filters(filters: list[str]) -> None:
    class Repo:
        pass

    validated_filters = eval_filters(filters, repo=Repo())  # pyre-ignore[6]
    filter_dict = {k: v for k, v in [f.split('=', 1) for f in filters]}

    for f in validated_filters:
        assert f.value == filter_dict[f.key]

    assert len(validated_filters) == len(filters)
    assert all(isinstance(f, Filter) for f in validated_filters)


@pytest.mark.parametrize('filters', [
    ['type=laptop', 'type=laptop'], ['badfilter']])
@pytest.mark.parametrize('rich', [True, False])
def test_eval_filters_error(capsys, filters: list[str], rich: bool) -> None:
    class Repo:
        pass

    with pytest.raises(SystemExit) as exc:
        _ = eval_filters(filters, repo=Repo(), rich=rich)  # pyre-ignore[6]

    captured = capsys.readouterr()
    if len(filters) > 1 and filters[0] == filters[1]:
        assert 'Duplicate filter keys: ' in captured.err
    else:
        assert 'Filters must be formatted as `key=value`' in captured.err

    assert str(exc.value) == '1'


def test_eval_keys() -> None:
    defaults = ['foo', 'bar']
    assert eval_keys(['a', 'b'], defaults) == ['a', 'b']
    assert eval_keys(['a', 'a'], defaults) == ['a']
    assert eval_keys([], defaults) == ['foo', 'bar']


def test_eval_path() -> None:
    defaults = {'.'}
    assert eval_path(['a', 'b'], defaults) == {'a', 'b'}
    assert eval_path(['a', 'a'], defaults) == {'a'}
    assert eval_path([], defaults) == {'.'}
