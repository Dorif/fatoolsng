# fileio/models.py
#
# models here are used to ensure the integrity and consistency of each
# inherited model

from fatoolsng.lib.utils import cerr  # , cout
from fatoolsng.lib.fautil.mixin import (MarkerMixIn, PanelMixIn, ChannelMixIn,
                                        FSAMixIn, AlleleMixIn)
from fatoolsng.lib import const
from pathlib import Path
from pickle import load as pickle_load, dump as pickle_dump


class Marker(MarkerMixIn):

    __slots__ = []

    container = {}

    @classmethod
    def upload(cls, d):
        for (k, v) in d.items():
            cls.container[k] = cls.from_dict(v)

    @classmethod
    def get_marker(cls, marker_code, species='x'):
        if '/' not in marker_code:
            marker_code = species + '/' + marker_code
        return cls.container[marker_code]


class Panel(PanelMixIn):

    __slots__ = []

    container = {}

    Marker = Marker

    @classmethod
    def upload(cls, d):
        for (k, v) in d.items():
            cls.container[k] = cls.from_dict(v)

    @classmethod
    def get_panel(cls, panel_code):
        return cls.container[panel_code]


class Allele(AlleleMixIn):

    __slots__ = []

    def __init__(self, rtime, rfu, area, brtime, ertime, wrtime, srtime,
                 beta, theta, omega):
        self.rtime = rtime
        self.rfu = rfu
        self.area = area
        self.brtime = brtime
        self.ertime = ertime
        self.wrtime = wrtime
        self.srtime = srtime
        self.beta = beta
        self.theta = theta
        self.omega = omega
        self.size = -1
        self.bin = -1
        self.dev = -1


class Channel(ChannelMixIn):

    __slots__ = []

    Allele = Allele

    def __init__(self, data, dye, wavelen, status, fsa):
        self.data = data
        self.dye = dye
        self.wavelen = wavelen
        self.status = status
        self.fsa = fsa

        self.alleles = []

        self.assign()

    def add_allele(self, allele):
        self.alleles.append(allele)
        return allele


class FSA(FSAMixIn):

    __slots__ = ['_fhdl', '_trace']

    Channel = Channel

    def __init__(self):
        self.channels = []
        self.excluded_markers = []

    def get_data_stream(self):
        return self._fhdl

    def add_channel(self, channel):
        self.channels.append(channel)
        return channel

    @classmethod
    def from_file(cls, fsa_filename, panel, excluded_markers=None,
                  cache=True, cache_path=None):
        fsa = cls()
        fsa.filename = Path(fsa_filename).name
        fsa.set_panel(panel, excluded_markers)
        # with fileio, we need to prepare channels everytime or seek from cache
        if cache_path is None:
            cache = False
        else:
            cache_file = Path(cache_path) / fsa.filename
        if cache and cache_file.exists():
            if Path(fsa_filename).stat().st_mtime < cache_file.stat().st_mtime:
                cerr(f'I: uploading channel cache for {fsa_filename}')
                try:
                    with open(cache_file, 'rb') as cache_handle_read:
                        fsa.channels = pickle_load(cache_handle_read)
                    for c in fsa.channels:
                        c.fsa = fsa
                    # assume channels are already normalized
                    fsa.status = const.assaystatus.normalized
                    return fsa
                except AttributeError:
                    cerr('E: uploading failed, will recreate cache')
        with open(fsa_filename, 'rb') as fsa_handle:
            fsa._fhdl = fsa_handle
            fsa.create_channels()
            fsa._fhdl = None
        if cache and Path(cache_path).exists():
            for c in fsa.channels:
                c.fsa = None
            with open(cache_file, 'wb') as cache_handle_write:
                pickle_dump(fsa.channels, cache_handle_write)
            for c in fsa.channels:
                c.fsa = fsa
        return fsa
