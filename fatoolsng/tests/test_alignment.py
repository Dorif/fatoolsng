"""Tests for the three advanced ladder alignment strategies:
align_gm  — Nelder-Mead generalised minimisation        (deterministic, fast)
align_de  — differential evolution                       (stochastic,   slow)
align_sh  — semi-heuristic: DE on subset + GM refinement (stochastic,   slow)

DE and SH tests are marked ``slow`` and skipped by default.
Run them explicitly with:  pytest -m slow
"""

import copy
import pytest

from fatoolsng.lib.fautil.algo import Peak, generate_scoring_function
from fatoolsng.lib.fautil.gmalign import align_gm, align_sh, align_de
from fatoolsng.lib.fautil.alignutils import AlignResult
from fatoolsng.lib.const import ladders, alignmethod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LIZ500_SIZES = [35, 50, 75, 100, 139, 150, 160, 200,
                 250, 300, 340, 350, 400, 450, 490, 500]

# A smaller subset — used for fast smoke tests of DE/SH so they finish quickly.
_MINI_SIZES = [75, 100, 139, 150, 160, 200, 250]


def _make_peaks(sizes, scale: float = 10.0, offset: int = 200,
                base_rfu: int = 1000) -> list[Peak]:
    """Synthetic peaks: rtime = size * scale + offset (linear relationship)."""
    peaks = []
    for i, size in enumerate(sizes):
        rtime = int(size * scale + offset)
        rfu = base_rfu + (i % 5) * 200
        peaks.append(Peak(
            rtime=rtime, rfu=rfu, area=rfu * 5,
            brtime=rtime - 5, ertime=rtime + 5,
            srtime=0.0, beta=8.0, theta=100.0, omega=rtime,
        ))
    return peaks


def _make_ladder(sizes):
    """Minimal ladder dict for a given size list."""
    n = len(sizes)
    return {
        'dye': 'LIZ',
        'sizes': sizes,
        'signature': sizes[:max(3, n // 2)],
        'order': 2,
        'k': max(2, n // 4),
        'a': 1,
        'strict': {'max_rss': 999.0, 'min_dpscore': 0.0,  'min_sizes': 1},
        'relax':  {'max_rss': 9999.0, 'min_dpscore': 0.0, 'min_sizes': 1},
        'qcfunc': generate_scoring_function(
            {'max_rss': 999.0,  'min_dpscore': 0.0, 'min_sizes': 1},
            {'max_rss': 9999.0, 'min_dpscore': 0.0, 'min_sizes': 1},
        ),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def liz500():
    """Full LIZ500 (16 sizes) — used for GM and slow DE/SH tests."""
    ladder = copy.deepcopy(dict(ladders['LIZ500']))
    ladder['qcfunc'] = generate_scoring_function(ladder['strict'], ladder['relax'])
    return _make_peaks(_LIZ500_SIZES), ladder


@pytest.fixture
def mini():
    """7-size mini-ladder — used for fast smoke tests of DE/SH."""
    return _make_peaks(_MINI_SIZES), _make_ladder(_MINI_SIZES)


@pytest.fixture
def anchor_pairs():
    return [(int(s * 10 + 200), s) for s in [75, 139, 200, 300, 400]]


# ---------------------------------------------------------------------------
# align_gm — Nelder-Mead (deterministic, ~3 s)
# ---------------------------------------------------------------------------

class TestAlignGm:

    def test_returns_align_result(self, liz500, anchor_pairs):
        peaks, ladder = liz500
        assert isinstance(align_gm(peaks, ladder, anchor_pairs), AlignResult)

    def test_score_is_float_in_range(self, liz500, anchor_pairs):
        result = align_gm(*liz500, anchor_pairs)
        assert 0.0 <= float(result.score) <= 1.0

    def test_method_is_gm(self, liz500, anchor_pairs):
        result = align_gm(*liz500, anchor_pairs)
        assert result.method in (alignmethod.gm_strict, alignmethod.gm_relax)

    def test_dpresult_not_none(self, liz500, anchor_pairs):
        assert align_gm(*liz500, anchor_pairs).dpresult is not None

    def test_perfect_data_scores_well(self, liz500, anchor_pairs):
        result = align_gm(*liz500, anchor_pairs)
        assert result.score > 0.5, (
            f"align_gm on perfect synthetic data scored {result.score:.3f}"
        )

    def test_sized_peaks_non_empty(self, liz500, anchor_pairs):
        result = align_gm(*liz500, anchor_pairs)
        assert len(result.dpresult.sized_peaks) > 0

    def test_z_polynomial_length(self, liz500, anchor_pairs):
        result = align_gm(*liz500, anchor_pairs)
        assert len(result.dpresult.z) >= 2


# ---------------------------------------------------------------------------
# align_de — fast smoke tests (mini fixture, skipped by default via 'slow')
# The full LIZ500 DE tests are marked slow — run with: pytest -m slow
# ---------------------------------------------------------------------------

class TestAlignDe:

    def test_smoke_mini(self, mini):
        """Fast smoke: 7 sizes, verifies align_de runs and returns AlignResult."""
        peaks, ladder = mini
        result = align_de(peaks, ladder)
        assert isinstance(result, AlignResult)
        assert 0.0 <= float(result.score) <= 1.0
        assert result.method == alignmethod.de_relax
        assert result.dpresult is not None
        assert len(result.dpresult.sized_peaks) > 0

    @pytest.mark.slow
    def test_returns_align_result(self, liz500):
        assert isinstance(align_de(*liz500), AlignResult)

    @pytest.mark.slow
    def test_score_is_float_in_range(self, liz500):
        result = align_de(*liz500)
        assert 0.0 <= float(result.score) <= 1.0

    @pytest.mark.slow
    def test_method_is_de_relax(self, liz500):
        assert align_de(*liz500).method == alignmethod.de_relax

    @pytest.mark.slow
    def test_dpresult_not_none(self, liz500):
        assert align_de(*liz500).dpresult is not None

    @pytest.mark.slow
    def test_sized_peaks_non_empty(self, liz500):
        assert len(align_de(*liz500).dpresult.sized_peaks) > 0


# ---------------------------------------------------------------------------
# align_sh — fast smoke tests (mini fixture), full tests marked slow
# ---------------------------------------------------------------------------

class TestAlignSh:

    def test_smoke_mini(self, mini):
        """Fast smoke: 7 sizes, verifies align_sh runs end-to-end."""
        peaks, ladder = mini
        result = align_sh(peaks, ladder)
        assert isinstance(result, AlignResult)
        assert 0.0 <= float(result.score) <= 1.0
        assert result.method in (alignmethod.sh_strict, alignmethod.sh_relax)
        assert result.dpresult is not None
        assert len(result.dpresult.sized_peaks) > 0

    def test_subset_peaks_present(self, liz500):
        """align_sh needs peaks in the 1500–5000 rtime range for its DE phase."""
        peaks, _ = liz500
        subset = [p for p in peaks if 1500 < p.rtime < 5000]
        assert len(subset) >= 3

    @pytest.mark.slow
    def test_returns_align_result(self, liz500):
        assert isinstance(align_sh(*liz500), AlignResult)

    @pytest.mark.slow
    def test_score_is_float_in_range(self, liz500):
        result = align_sh(*liz500)
        assert 0.0 <= float(result.score) <= 1.0

    @pytest.mark.slow
    def test_method_is_sh(self, liz500):
        result = align_sh(*liz500)
        assert result.method in (alignmethod.sh_strict, alignmethod.sh_relax)

    @pytest.mark.slow
    def test_dpresult_not_none(self, liz500):
        assert align_sh(*liz500).dpresult is not None

    @pytest.mark.slow
    def test_sized_peaks_non_empty(self, liz500):
        assert len(align_sh(*liz500).dpresult.sized_peaks) > 0
