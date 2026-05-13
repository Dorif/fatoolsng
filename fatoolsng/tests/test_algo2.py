import pytest
from fatoolsng.lib.fautil.algo2 import Peak, Channel


class TestPeak:

    def test_all_defaults_are_minus_one(self):
        p = Peak()
        for field in ('rtime', 'rfu', 'area', 'brtime', 'ertime', 'omega', 'bin'):
            assert getattr(p, field) == -1, f'{field} default should be -1'
        for field in ('srtime', 'beta', 'theta', 'size'):
            assert getattr(p, field) == -1, f'{field} default should be -1'

    def test_custom_construction(self):
        p = Peak(rtime=1500, rfu=2000, area=5000,
                 brtime=1490, ertime=1510,
                 srtime=0.1, beta=8.0, theta=100.0, omega=1234)
        assert p.rtime == 1500
        assert p.rfu == 2000
        assert p.area == 5000
        assert p.brtime == 1490
        assert p.ertime == 1510

    def test_repr_contains_rtime(self):
        p = Peak(rtime=1500, rfu=200, area=800,
                 brtime=1490, ertime=1510,
                 srtime=0.0, beta=5.0, theta=50.0, omega=100)
        r = repr(p)
        assert '<P:' in r
        assert '1500' in r

    def test_repr_does_not_use_default_repr(self):
        # @dataclass(repr=False) with custom __repr__ — should NOT show 'Peak('
        p = Peak(rtime=100, rfu=50, area=200,
                 brtime=95, ertime=105,
                 srtime=0.0, beta=4.0, theta=30.0, omega=50)
        assert 'Peak(' not in repr(p)

    def test_size_and_bin_settable(self):
        p = Peak()
        p.size = 150.3
        p.bin = 150
        assert p.size == 150.3
        assert p.bin == 150


class TestChannel:

    def test_required_fields(self):
        ch = Channel(data=[1, 2, 3], marker='ladder')
        assert ch.data == [1, 2, 3]
        assert ch.marker == 'ladder'

    def test_alleles_default_empty_list(self):
        ch = Channel(data=[], marker=None)
        assert ch.alleles == []
        assert isinstance(ch.alleles, list)

    def test_alleles_not_shared_between_instances(self):
        # Regression for mutable default — must use field(default_factory=list)
        ch1 = Channel(data=[], marker=None)
        ch2 = Channel(data=[], marker=None)
        ch1.alleles.append('peak')
        assert ch2.alleles == [], \
            'Channel.alleles must not be shared across instances'

    def test_fsa_defaults_to_none(self):
        ch = Channel(data=[], marker=None)
        assert ch.fsa is None

    def test_fsa_settable(self):
        ch = Channel(data=[], marker=None, fsa='mock_fsa')
        assert ch.fsa == 'mock_fsa'
