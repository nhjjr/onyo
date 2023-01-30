import pytest
from pathlib import Path

from onyo.lib import Filter, OnyoInvalidFilterError


@pytest.mark.parametrize('filt', ['type=laptop', 'key=value', 'foo=<unset>'])
def test_filter(filt: str) -> None:
    class Repo:
        def _read_asset(self, asset: Path):
            if asset.name == 'laptop_make_model.1':
                return {'key': 'value'}
            elif asset.name == 'monitor_make_model.2':
                return {'foo': 'bar'}
            elif asset.name == 'headphones_make_model.3':
                return {}
            elif asset.name == 'wheelchair_make_model.4':
                return {'foo': None}
            elif asset.name == 'wheelchair_make_model.4':
                return {'foo': ''}

    f = Filter(filt, repo=Repo())  # pyre-ignore[6]
    assert f.key == filt.split('=', 1)[0]
    assert f.value == filt.split('=', 1)[1]
    assert f.is_default if filt.split('=', 1)[0] in f._default_keys \
        else not f.is_default
    assert f.match(Path('laptop_make_model.1'))
    assert not f.match(Path('monitor_make_model.2'))

    if filt.split('=', 1)[1] == '<unset>':
        assert f.match(Path('headphones_make_model.3'))
        assert f.match(Path('wheelchair_make_model.4'))
    else:
        assert not f.match(Path('headphones_make_model.3'))
        assert not f.match(Path('wheelchair_make_model.4'))


@pytest.mark.parametrize('filt', ['key=<list>', 'key=<dict>'])
def test_filter_match_type(filt: str) -> None:
    class Repo:
        def _read_asset(self, asset: Path):
            if asset.name == 'type_make_model.1':
                return {'key': ['a', 'b', 'c']}
            elif asset.name == 'type_make_model.2':
                return {'key': {'a': 'b', 'c': 'd'}}

    string_type = filt.split('=', 1)[1]
    f = Filter(filt, repo=Repo())  # pyre-ignore[6]
    if string_type == '<list>':
        assert f.match(Path('type_make_model.1'))
        assert not f.match(Path('type_make_model.2'))
    elif string_type == '<dict>':
        assert not f.match(Path('type_make_model.1'))
        assert f.match(Path('type_make_model.2'))


def test_filter_re_match() -> None:
    assert not Filter._re_match(text='foo(', r='foo(')
    assert Filter._re_match(text='foo', r='foo')
    assert Filter._re_match(text='foobar', r='foo.*')


@pytest.mark.parametrize('filter_arg', [
    'key', 'key!value', '┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻'])
def test_filter_invalid(filter_arg: str) -> None:
    class Repo:
        def _read_asset(self, asset: Path):
            return {'foo': 'bar', 'key': 'value and more'}

    with pytest.raises(OnyoInvalidFilterError) as exc:
        _ = Filter('key', repo=Repo())  # pyre-ignore[6]

    assert 'Filters must be formatted as `key=value`' in str(exc.value)


def test_filter_format() -> None:
    assert Filter._format('key=value') == ['key', 'value']
    assert Filter._format('key=value=value') == ['key', 'value=value']
