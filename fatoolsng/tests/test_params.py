import pytest
from fatoolsng.lib.params import (
    ScanningParameter, LadderScanningParameter, Params,
    default_panels, default_markers,
)


class TestScanningParameter:

    def test_default_method(self):
        p = ScanningParameter()
        assert p.method == 'pd'

    def test_default_numeric_fields(self):
        p = ScanningParameter()
        assert p.min_height >= 0
        assert p.min_snr > 0
        assert p.max_peak_number > 0
        assert p.min_rtime < p.max_rtime

    def test_widths_non_empty(self):
        p = ScanningParameter()
        assert len(p.widths) > 0

    def test_independent_instances(self):
        p1 = ScanningParameter()
        p2 = ScanningParameter()
        p1.method = 'cwt'
        assert p2.method == 'pd'


class TestLadderScanningParameter:

    def test_inherits_scanning_parameter(self):
        p = LadderScanningParameter()
        assert isinstance(p, ScanningParameter)

    def test_ladder_specific_values(self):
        p = LadderScanningParameter()
        assert p.expected_peak_number == 36
        assert p.min_rtime == 1
        assert p.min_snr == 1.25

    def test_ladder_widths_narrower_than_nonladder(self):
        ladder = LadderScanningParameter()
        nonladder = ScanningParameter()
        assert max(ladder.widths) < max(nonladder.widths)


class TestParams:

    def test_has_ladder_and_nonladder(self):
        p = Params()
        assert isinstance(p.ladder, LadderScanningParameter)
        assert isinstance(p.nonladder, ScanningParameter)

    def test_ladder_expected_peaks_set(self):
        p = Params()
        assert p.ladder.expected_peak_number > 0

    def test_nonladder_expected_peaks_zero(self):
        p = Params()
        assert p.nonladder.expected_peak_number == 0


class TestDefaultPanels:

    def test_known_panels_present(self):
        assert 'GS600LIZ' in default_panels
        assert 'GS500LIZ' in default_panels
        assert 'undefined' in default_panels

    def test_panel_structure(self):
        panel = default_panels['GS600LIZ']
        assert panel['code'] == 'GS600LIZ'
        assert 'ladder' in panel['data']
        assert 'markers' in panel['data']

    def test_gs600_uses_liz600(self):
        assert default_panels['GS600LIZ']['data']['ladder'] == 'LIZ600'

    def test_gs500_uses_liz500(self):
        assert default_panels['GS500LIZ']['data']['ladder'] == 'LIZ500'

    def test_gs600_has_four_dyes(self):
        markers = default_panels['GS600LIZ']['data']['markers']
        dyes_used = {v['dye'] for v in markers.values()}
        assert dyes_used == {'VIC', 'PET', 'NED', '6-FAM'}


class TestDefaultMarkers:

    def test_required_markers_present(self):
        for key in ('x/ladder', 'x/undefined', 'x/VIC', 'x/NED', 'x/PET', 'x/6-FAM'):
            assert key in default_markers

    def test_marker_size_range(self):
        for key, marker in default_markers.items():
            if 'min_size' in marker and 'max_size' in marker:
                if marker['min_size'] >= 0:
                    assert marker['min_size'] < marker['max_size'], \
                        f'{key}: min_size must be < max_size'
