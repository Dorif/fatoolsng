import pickle
import pytest
from pathlib import Path
from fatoolsng.lib.fautil.peakcache import PeakCache


@pytest.fixture
def cache(tmp_path):
    db = PeakCache(tmp_path / 'peaks.db')
    yield db
    db.close()


class TestReadWrite:

    def test_put_and_get_bytes_key(self, cache):
        cache.put(b'batch|sample|file|ts|FAM', b'\x01\x02\x03')
        assert cache.get(b'batch|sample|file|ts|FAM') == b'\x01\x02\x03'

    def test_put_and_get_str_key(self, cache):
        cache.put('key1', b'value1')
        assert cache.get('key1') == b'value1'

    def test_str_and_bytes_keys_are_equivalent(self, cache):
        cache.put('mykey', b'data')
        assert cache.get(b'mykey') == b'data'

    def test_get_missing_returns_none(self, cache):
        assert cache.get('nonexistent') is None

    def test_get_missing_returns_custom_default(self, cache):
        assert cache.get('nonexistent', b'fallback') == b'fallback'

    def test_capital_Get_alias(self, cache):
        cache.put(b'k', b'v')
        assert cache.Get(b'k') == b'v'

    def test_capital_Put_alias(self, cache):
        cache.Put(b'k2', b'v2')
        assert cache.get(b'k2') == b'v2'

    def test_overwrite_existing_key(self, cache):
        cache.put('k', b'first')
        cache.put('k', b'second')
        assert cache.get('k') == b'second'

    def test_pickled_peaks_roundtrip(self, cache):
        peaks = [(100, 2000, 5000, 90, 110), (200, 1500, 3000, 190, 210)]
        key = b'batch1|sampleA|run.fsa|20240101|VIC'
        cache.put(key, pickle.dumps(peaks))
        result = pickle.loads(cache.get(key))
        assert result == peaks


class TestIterator:

    def test_iterator_keys_only(self, cache):
        cache.put('a|1', b'x')
        cache.put('b|2', b'y')
        keys = list(cache.iterator(include_value=False))
        assert b'a|1' in keys
        assert b'b|2' in keys

    def test_iterator_with_values(self, cache):
        cache.put('k', b'v')
        pairs = list(cache.iterator(include_value=True))
        assert (b'k', b'v') in pairs

    def test_iterator_ordered_by_key(self, cache):
        for ch in 'cba':
            cache.put(ch, b'')
        keys = list(cache.iterator(include_value=False))
        assert keys == sorted(keys)

    def test_iterator_empty_db(self, cache):
        assert list(cache.iterator(include_value=False)) == []

    def test_iterator_key_split_compatible(self, cache):
        """Keys must be splittable on b'|' as dbmgr.do_viewpeakcachedb does."""
        cache.put('batch1|sampleA|run.fsa|20240101|FAM', b'data')
        for key in cache.iterator(include_value=False):
            batch_code = key.split(b'|', 1)[0]
            assert batch_code == b'batch1'


class TestPersistence:

    def test_data_survives_close_and_reopen(self, tmp_path):
        path = tmp_path / 'peaks.db'
        with PeakCache(path) as db:
            db.put('persistent_key', b'persistent_value')

        with PeakCache(path, create_if_missing=False) as db:
            assert db.get('persistent_key') == b'persistent_value'

    def test_create_if_missing_false_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PeakCache(tmp_path / 'does_not_exist.db', create_if_missing=False)

    def test_context_manager(self, tmp_path):
        path = tmp_path / 'ctx.db'
        with PeakCache(path) as db:
            db.put('x', b'y')
            assert db.get('x') == b'y'
