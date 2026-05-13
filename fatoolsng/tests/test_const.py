from fatoolsng.lib.const import (
    peaktype, channelstatus, assaystatus, alignmethod,
    scanningmethod, allelemethod, binningmethod, dyes, ladders,
)


class TestStrEnumBehavior:

    def test_members_equal_their_string_values(self):
        assert peaktype.scanned == 'scanned'
        assert peaktype.noise == 'noise'
        assert channelstatus.aligned == 'aligned'
        assert assaystatus.called == 'called'
        assert alignmethod.fast_hq == 'fast|highqual'
        assert scanningmethod.cwt == 'cwt'
        assert allelemethod.cubicspline == 'cubicspline'
        assert binningmethod.auto == 'auto'

    def test_members_are_strings(self):
        assert isinstance(peaktype.scanned, str)
        assert isinstance(channelstatus.ladder, str)

    def test_members_are_distinct(self):
        assert peaktype.scanned != peaktype.noise
        assert channelstatus.assigned != channelstatus.unassigned

    def test_enum_membership(self):
        assert peaktype.scanned in peaktype
        assert 'scanned' in [m.value for m in peaktype]

    def test_peaktype_count(self):
        assert len(list(peaktype)) == 11

    def test_channelstatus_count(self):
        assert len(list(channelstatus)) == 13

    def test_alignmethod_contains_pipe_values(self):
        # Pipe separates algorithm family from quality tier
        assert '|' in alignmethod.fast_hq
        assert '|' in alignmethod.greedy_filtered


class TestDyes:

    def test_standard_dyes_present(self):
        for dye in ['6-FAM', 'NED', 'VIC', 'PET', 'LIZ']:
            assert dye in dyes

    def test_dyes_is_list(self):
        assert isinstance(dyes, list)


class TestLadders:

    def test_known_ladders_present(self):
        assert 'LIZ600' in ladders
        assert 'LIZ500' in ladders

    def test_liz600_structure(self):
        l = ladders['LIZ600']
        assert 'sizes' in l
        assert 'strict' in l
        assert 'relax' in l
        assert 'signature' in l
        assert l['dye'] == 'LIZ'

    def test_liz600_size_count(self):
        assert len(ladders['LIZ600']['sizes']) == 36

    def test_liz500_size_count(self):
        assert len(ladders['LIZ500']['sizes']) == 16

    def test_sizes_are_sorted(self):
        for name, ladder in ladders.items():
            sizes = ladder['sizes']
            assert sizes == sorted(sizes), f'{name} sizes are not sorted'

    def test_qc_thresholds_present(self):
        for tier in ('strict', 'relax'):
            for key in ('max_rss', 'min_dpscore', 'min_sizes'):
                assert key in ladders['LIZ600'][tier]
                assert key in ladders['LIZ500'][tier]

    def test_strict_tighter_than_relax(self):
        for name, ladder in ladders.items():
            strict = ladder['strict']
            relax = ladder['relax']
            assert strict['max_rss'] <= relax['max_rss'], \
                f'{name}: strict max_rss should be ≤ relax max_rss'
            assert strict['min_dpscore'] >= relax['min_dpscore'], \
                f'{name}: strict min_dpscore should be ≥ relax min_dpscore'
