import pytest
from fatoolsng.lib.fautil.alignutils import (
    AlignResult, DPResult, ZResult, PeakPairs, estimate_z,
)


class TestDataclasses:

    def test_alignresult_fields(self):
        ar = AlignResult(score=0.95, msg='ok', dpresult=None, method='fast')
        assert ar.score == 0.95
        assert ar.msg == 'ok'
        assert ar.dpresult is None
        assert ar.method == 'fast'
        assert ar.initial_pairs is None  # default

    def test_alignresult_with_initial_pairs(self):
        pairs = [(100, 50.0)]
        ar = AlignResult(score=0.8, msg=None, dpresult=None, method='greedy',
                         initial_pairs=pairs)
        assert ar.initial_pairs == pairs

    def test_dpresult_fields(self):
        dr = DPResult(dpscore=35.0, rss=12.5, z=[1, 2, 3], sized_peaks=[])
        assert dr.dpscore == 35.0
        assert dr.rss == 12.5
        assert dr.sized_peaks == []

    def test_dpresult_ztranspose_empty_when_no_peaks(self):
        dr = DPResult(dpscore=0, rss=0, z=[], sized_peaks=[])
        assert dr.ztranspose == []

    def test_zresult_fields(self):
        zr = ZResult(z=[1.0, 2.0], rss=0.001, f=None)
        assert zr.rss == 0.001


class TestPeakPairs:

    def test_basic_construction(self):
        pairs = [(100, 50.0), (200, 100.0), (300, 150.0)]
        pp = PeakPairs(pairs)
        assert pp.r2s[100] == 50.0
        assert pp.r2s[300] == 150.0

    def test_s2r_mapping(self):
        pairs = [(100, 50.0), (200, 100.0)]
        pp = PeakPairs(pairs)
        assert pp.s2r[50.0] == 100
        assert pp.s2r[100.0] == 200

    def test_preserves_all_pairs(self):
        pairs = [(i * 100, float(i * 50)) for i in range(1, 6)]
        pp = PeakPairs(pairs)
        assert len(pp.pairs) == 5


class TestEstimateZ:

    def test_perfect_linear_fit(self):
        # y = 2x + 1
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [3.0, 5.0, 7.0, 9.0, 11.0]
        result = estimate_z(x, y, degree=1)
        assert isinstance(result, ZResult)
        assert float(result.rss) < 1e-5

    def test_function_callable_and_accurate(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [3.0, 5.0, 7.0, 9.0, 11.0]
        result = estimate_z(x, y, degree=1)
        assert abs(float(result.f(3.0)) - 7.0) < 1e-4
        assert abs(float(result.f(6.0)) - 13.0) < 1e-4

    def test_rss_is_non_negative(self):
        x = [100, 200, 300, 400, 500]
        y = [20, 45, 68, 95, 118]  # roughly linear with noise
        result = estimate_z(x, y, degree=1)
        assert float(result.rss) >= 0

    def test_higher_degree_better_fit(self):
        # Quadratic data — degree 2 should fit better than degree 1
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 4.0, 9.0, 16.0, 25.0]  # y = x^2
        r1 = estimate_z(x, y, degree=1)
        r2 = estimate_z(x, y, degree=2)
        assert float(r2.rss) < float(r1.rss)

    def test_z_polynomial_length(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        for degree in (1, 2, 3):
            result = estimate_z(x, y, degree=degree)
            assert len(result.z) == degree + 1
