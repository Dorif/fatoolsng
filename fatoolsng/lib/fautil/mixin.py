from __future__ import annotations

from fatoolsng.lib.fautil import algo
from fatoolsng.lib.utils import cout, cerr  # , cexit
from fatoolsng.lib import const
from abc import ABC, abstractmethod
from typing import Any, BinaryIO

from time import process_time

# FA


class AlleleMixIn:

    __slots__ = ['rtime', 'rfu', 'area', 'brtime', 'ertime', 'wrtime',
                 'srtime', 'beta', 'theta', 'omega', 'size', 'bin', 'dev',
                 'type', 'method', 'marker', 'qscore', 'qcall',]

    def __repr__(self):
        return (f"<A: {self.size:3d} | {self.rtime:4d} | {self.rfu:5d} | {self.wrtime:2d}"
                f" | {self.srtime:+3.1f} | {self.beta:4.1f} | {self.theta:5.1f}"
                f" | {self.omega:6d} | {self.dev:4.2f} >")

    @property
    def height(self):
        return self.rfu

    def __lt__(self, other):
        return self.rtime < other.rtime


class AlleleSetMixIn:
    pass


class ChannelMixIn(ABC):
    """
    attrs: alleles, fsa, status
    """

    __slots__ = ['data', 'dye', 'wavelen', 'alleles', 'fsa', 'status',
                 'marker', 'mma', 'mmb', 'p80', 'offset',]

    @abstractmethod
    def add_allele(self, allele: Any) -> None:
        """ add this allele to channel """
        ...

    def is_ladder(self) -> bool:
        return self.marker.code == 'ladder'

    def assign(self):
        marker = self.fsa.panel.get_marker(self.dye)
        if marker.label.lower() in self.fsa.excluded_markers:
            self.marker = self.fsa.panel.get_marker('undefined')
        else:
            self.marker = marker

    def get_alleles(self) -> list:
        if self.status == const.channelstatus.reseted:
            # create alleles first
            raise RuntimeError('E: channel needs to be scanned first')
        return self.alleles

    def scan(self, parameters: Any = None) -> None:
        if self.status != const.channelstatus.reseted:
            return

        alleles = algo.scan_peaks(self, parameters.ladder
                                  if self.is_ladder()
                                  else parameters.nonladder)

        # import pprint; pprint.pprint(alleles)

#    def preannotate(self, parameters):
#        pass

    def align(self, parameters=None, anchor_pairs=None):

        # sanity checks
        if self.marker.code != 'ladder':
            raise RuntimeError('E: align() must be performed on ladder channel!')

        if parameters:
            self.scan(parameters)  # in case this channel hasn't been scanned

        ladder = self.fsa.panel.get_ladder()

        # prepare ladder qcfunc
        if 'qcfunc' not in ladder:
            ladder['qcfunc'] = algo.generate_scoring_function(ladder['strict'],
                                                              ladder['relax'])

        start_time = process_time()
        result = algo.align_peaks(self, parameters, ladder, anchor_pairs)
        dpresult = result.dpresult
        fsa = self.fsa
        fsa.z = dpresult.z
        fsa.rss = dpresult.rss
        fsa.nladder = len(dpresult.sized_peaks)
        fsa.score = result.score
        fsa.duration = process_time() - start_time
        fsa.status = const.assaystatus.aligned
        fsa.ztranspose = dpresult.ztranspose

        # import pprint; pprint.pprint(dpresult.sized_peaks)
        # print(fsa.z)
        cout(f"O: Score {fsa.score:3.2f} | {fsa.rss:5.2f} | {fsa.nladder}/{len(ladder['sizes'])} | {result.method} | {fsa.duration:5.1f} | {fsa.filename}")

    def call(self, parameters, func, min_rtime, max_rtime):

        if parameters:
            self.scan(parameters)

        algo.call_peaks(self, parameters, func, min_rtime, max_rtime)

    def __repr__(self):
        return f"<Channel: {self.dye}> "


class FSAMixIn(ABC):
    """
    attrs: channels
    """

    __slots__ = ['panel', 'channels', 'excluded_markers', 'filename', 'rss',
                 'z', 'score', 'nladder', 'duration', 'status', 'ztranspose',]

    @abstractmethod
    def get_data_stream(self) -> BinaryIO:
        """ return stream of data """
        ...

    @abstractmethod
    def add_channel(self, trace_channel: Any) -> None:
        """ add this channel to fsa """
        ...

    def get_trace(self):
        if not hasattr(self, '_trace'):
            from fatoolsng.lib.fautil import traceio
            self._trace = traceio.read_abif_stream(self.get_data_stream())
        return self._trace

    def set_panel(self, panel, options=None):
        """ set panel and add excluded markers """
        self.panel = panel

        if not options:
            return

        excluded_markers = [x.strip() for x in options['exclude'].split(',')]

        for marker_code in excluded_markers:
            if panel.has_marker(marker_code):
                self.excluded_markers.append(marker_code.lower())

    def create_channels(self):
        cerr(f'I: Generating channels for {self.filename}')
        trace = self.get_trace()
        trace_channels = algo.separate_channels(trace)
        for tc in trace_channels:
            channel = self.Channel(data=tc.smooth_channel, dye=tc.dye_name,
                                   wavelen=tc.dye_wavelength,
                                   status=const.channelstatus.reseted,
                                   fsa=self)
            self.add_channel(channel)
            # channel.status = const.channelstatus.reseted
        self.status = const.assaystatus.normalized

    def align(self, parameters: Any = None) -> tuple[float, float, int]:
        """ return (score, rss, nladder)
        """

        # check if this FSA has not been aligned previously
        if self.status != const.assaystatus.normalized:
            return (self.score, self.rss, self.nladder)

        c = self.get_ladder_channel()

        c.align(parameters)
        alleles = c.get_alleles()

        return (self.score, self.rss, self.nladder)

    def call(self, parameters: Any, marker: Any = None) -> None:

        ladder = self.get_ladder_channel()

        # sanity check to ensure FSA has been aligned with size ladders
        if ladder.status != const.channelstatus.aligned:
            self.align(parameters)

        # prepare ladders and calling function
        ladders = [p for p in ladder.get_alleles() if p.size > 0]
        ladders.sort(key=lambda x: x.size)
        func = algo.local_southern(ladders)
        min_rtime = ladders[1].rtime
        max_rtime = ladders[-2].rtime

        for c in self.channels:
            if c == ladder:
                continue
            c.call(parameters, func, min_rtime, max_rtime)
        self.status = const.assaystatus.called

    def scan(self, params: Any, peakdb: Any = None) -> None:
        """ scan all channels for peaks """
        for c in self.channels:
            c.scan(params)
        self.status = const.assaystatus.scanned

    def clear(self) -> None:
        """ clear all alleles and reset status """
        self.status = const.assaystatus.assigned
        for c in self.channels:
            c.alleles = []
            c.status = const.channelstatus.reseted

    def bin(self, params: Any, markers: list | None = None) -> None:
        """ bin non-ladder channels """
        ladder = self.get_ladder_channel()
        for c in self.channels:
            if c == ladder:
                continue
            if markers and c.marker not in markers:
                continue
            c.bin(params, c.marker)

    def get_ladder_channel(self) -> Any:

        for c in self.channels:
            if c.marker.code == 'ladder':
                return c
        raise RuntimeError('E: ladder channel not found')


class MarkerMixIn:
    """
    attrs: id, code, species, min_size, max_size, repeats, z_params
    """

    __slots__ = ['id', 'code', 'species', 'repeats', 'min_size', 'max_size',]

    def update(self, obj):

        if isinstance(obj, dict):
            if hasattr(self, 'id') and self.id is not None:
                raise RuntimeError('ERR: can only update from dictionary on new instance')
            if 'code' in obj:
                self.code = obj['code']
            if 'species' in obj:
                self.species = obj['species']
            if 'min_size' in obj:
                self.min_size = obj['min_size']
            if 'max_size' in obj:
                self.max_size = obj['max_size']
            if 'repeats' in obj:
                self.repeats = obj['repeats']
            if 'z_params' in obj:
                self.z_params = obj['z_params']

            # field 'related_to' must be handled by implementation object

        else:
            if self.code != obj.code:
                raise RuntimeError('ERR: attempting to update Marker with different code')
            if obj.min_size is not None:
                self.min_size = obj.min_size
            if obj.max_size is not None:
                self.max_size = obj.max_size
            if obj.repeats is not None:
                self.repeats = obj.repeats
            if obj.related_to is not None:
                self.related_to = obj.related_to
            if obj.z_params is not None:
                self.z_params = obj.z_params

    @property
    def label(self) -> str:
        return f'{self.species}/{self.code}'

    @classmethod
    def from_dict(cls, d):
        marker = cls()
        marker.update(d)
        return marker


class PanelMixIn(ABC):
    """
    attrs: id, code, data, dyes, Marker
    """

    __slots__ = ['id', 'code', 'data', 'dyes', '_dyes',]

    @abstractmethod
    def set_ladder_dye(self, ladder: dict) -> None:
        ...

    def update(self, obj):

        if isinstance(obj, dict):
            self.code = obj['code']
            self.data = obj['data']

        else:
            raise NotImplementedError()

    def get_markers(self):
        """ return all instance of markers """
        return [self.Marker.get_marker(code) for code in self.data['markers']]

    def get_marker(self, dye):
        if not hasattr(self, '_dyes') or not self._dyes:
            self._dyes = {}
            for m in self.get_markers():
                self._dyes[self.data['markers'][m.label]['dye']] = m
            ladder = self.get_ladder()
            self._dyes[ladder['dye']] = self.Marker.get_marker('ladder')
        return self._dyes[dye]

    def get_ladder(self):
        return const.ladders[self.data['ladder']]

    @classmethod
    def from_dict(cls, d):
        panel = cls()
        panel.update(d)
        return panel


class BinMixIn:
    pass

# Sample


class SampleMixIn:
    pass


class BatchMixIn:
    pass


# Auxiliary mixin, probably should be in separate file when fully implemented

class NoteMixIn:
    pass


class BatchNoteMixIn:
    pass


class SampleNoteMixIn:
    pass


class MarkerNoteMixIn:
    pass


class PanelNoteMixIn:
    pass


class FSANoteMixIn:
    pass


class ChannelNoteMixIn:
    pass


class AlleleSetNoteMixIn:
    pass
