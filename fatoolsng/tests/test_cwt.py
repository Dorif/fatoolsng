import pytest
from numpy import linspace, exp, zeros, ones, arange
from fatoolsng.lib.fautil.traceutils import _cwt_find_peaks


def gaussian_peak(center, width, n=200):
    x = linspace(0, n - 1, n)
    return exp(-((x - center) ** 2) / (2 * width ** 2))


class TestCwtFindPeaks:

    def test_single_clear_peak(self):
        signal = gaussian_peak(center=100, width=5)
        widths = arange(2, 12)
        peaks = _cwt_find_peaks(signal, widths, min_snr=0.1)
        assert len(peaks) >= 1
        assert any(abs(p - 100) < 15 for p in peaks)

    def test_flat_signal_no_peaks(self):
        signal = zeros(200)
        widths = arange(2, 8)
        peaks = _cwt_find_peaks(signal, widths)
        assert len(peaks) == 0

    def test_constant_nonzero_signal_no_interior_peaks(self):
        # CWT convolution produces boundary artifacts at the edges of a flat signal;
        # the interior (10%–90%) must have no peaks.
        signal = ones(200) * 500.0
        widths = arange(2, 8)
        peaks = _cwt_find_peaks(signal, widths)
        interior = [p for p in peaks if 20 < p < 180]
        assert len(interior) == 0

    def test_two_separated_peaks(self):
        signal = (gaussian_peak(center=50, width=4) +
                  gaussian_peak(center=150, width=4))
        widths = arange(2, 12)
        peaks = _cwt_find_peaks(signal, widths, min_snr=0.1)
        assert len(peaks) >= 2

    def test_returns_array_like(self):
        signal = gaussian_peak(center=100, width=5)
        widths = arange(2, 8)
        result = _cwt_find_peaks(signal, widths)
        assert hasattr(result, '__len__')

    def test_high_snr_threshold_suppresses_small_peaks(self):
        # Strong peak at 100, tiny bump at 150
        signal = gaussian_peak(center=100, width=5) + 0.05 * gaussian_peak(center=150, width=3)
        widths = arange(2, 12)
        low_snr = _cwt_find_peaks(signal, widths, min_snr=0.01)
        high_snr = _cwt_find_peaks(signal, widths, min_snr=5.0)
        assert len(high_snr) <= len(low_snr)
