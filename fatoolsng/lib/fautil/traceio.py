# traceio.py
'''
Copyright (C) 2004-2015 Hidayat Trimarsanto <anto@eijkman.go.id>
Eijkman Institute for Molecular Biology

This module is part of seqpy, a set of python scripts for sequence processing
and is released under GNU General Public License version 3 or later:
http://www.gnu.org/licenses/gpl.html
'''

__version__ = '20081006a'

import struct
from sys import argv, stderr
from jax.numpy import array
import datetime
from traceutils import smooth_signal, correct_baseline

DEBUG = False


def D(text):
    if DEBUG:
        print(text, file=stderr, flush=True)


def b(txt):
    return txt.encode('ASCII')

# --------------------------- ABIF format -------------------------------
#
# Format specs are available at:
# http://www6.appliedbiosystems.com/support/software_community/ABIF_File_Format.pdf
#


abitypes = {1: '%dB', 18: 'x%ds', 19: '%ds', 2: '%ds', 201: '%db', 4: '>%dh',
            5: '>%dl', 7: '>%df', 8: '>%dd', 10: '>1h2B',  # 10: '4s',
            11: '>4B', 13: '%ds', 1024: '%ds'}


abitags = {b'GELP1': 2, b'PCON1': 201}


abif_direntry = '>4slhhll4sl'


class ABIF_DirEntry(object):

    def __init__(self, tag, no, etype, esize, num, dsize, drec, dhdl):
        self.tag = tag
        self.no = no
        self.etype = etype
        self.esize = esize
        self.num = num
        self.dsize = dsize
        self.drec = drec
        self.data = None

    def set_data(self, data):
        self.data = data
        self.num = len(data)

    def get_data(self):
        return self.data

    def __repr__(self):
        if self.etype in [18, 19]:
            return '<ABIF etype: %s, data: "%s">' % (self.etype, self.data)
        elif self.num < 10 and self.etype not in [10, 11]:
            return '<ABIF etype: %s, data: %s>' % (self.etype, str(self.data))
        return '<ABIF etype: %s, size: %d>' % (self.etype, self.num)


class ABIF_Channel(object):

    def __init__(self, dye_name, wavelength, trace):
        self.dye_name = dye_name
        self.wavelength = wavelength
        self.raw = trace
        self._smooth = None

    def smooth(self):
        """ return savitsky-golay transformation of raw data """
        if self._smooth is None:
            self._smooth = correct_baseline(smooth_signal(self.raw))
        return self._smooth


class ABIF(object):

    def __init__(self):
        self.dir_entries = {}
        self.version = None

    def get_entry(self, tagno):
        tag, no = tagno[:4], int(tagno[4:])
        return self.dir_entries[tag][no]

    def get_data(self, tagno):
        return self.get_entry(tagno).get_data()

    def to_seqtrace(self):
        t = SeqTrace()
        t.original_trace = self
        t.num = self.get_entry(b'DATA12').num
        t.bases = self.get_data(b'PBAS1')
        t.basecalls = self.get_data(b'PLOC1')
        try:
            t.quality = self.get_data(b'PCON1')
            t.prob_A = t.prob_C = t.prob_G = t.prob_T = t.quality
        except KeyError:
            pass
        order = self.get_data(b'FWO_1')
        order.upper()
        t.trace_A = self.get_data(('DATA%d' %
                                   (9 + order.index(b'A'))).encode('ASCII'))
        t.trace_C = self.get_data(('DATA%d' %
                                   (9 + order.index(b'C'))).encode('ASCII'))
        t.trace_G = self.get_data(('DATA%d' %
                                   (9 + order.index(b'G'))).encode('ASCII'))
        t.trace_T = self.get_data(('DATA%d' %
                                   (9 + order.index(b'T'))).encode('ASCII'))

        return t

# return a list of ['dye name', dye_wavelength, numpy_array, numpy_smooth]
    def get_channels(self):
        results = {}
        for (idx, data_idx) in [(1, 1), (2, 2), (3, 3), (4, 4), (5, 105)]:
            try:
                dye_name = self.get_data(b('DyeN%d' % idx)).decode('ASCII')
                # below is to workaround on some strange dye name
                if dye_name == '6FAM':
                    dye_name = '6-FAM'
                elif dye_name == 'PAT':
                    dye_name = 'PET'
                elif dye_name == 'Bn Joda':
                    dye_name = 'LIZ'
                try:
                    dye_wavelength = self.get_data(b('DyeW%d' % idx))
                except KeyError:
                    dye_wavelength = WAVELENGTH[dye_name]
                raw_channel = array(self.get_data(b('DATA%d' % data_idx)))

                results[dye_name] = ABIF_Channel(dye_name, dye_wavelength,
                                                 raw_channel)

            except KeyError:
                pass

        return results

    def get_run_start_time(self):

        rdate = self.get_data(b'RUND1')
        rtime = self.get_data(b'RUNT1')
        return datetime.datetime(rdate[0], rdate[1], rdate[2], rtime[0],
                                 rtime[1], rtime[2])


def read_abif_stream(istream):

    bdata = istream.read()

    if not bdata.startswith(b'ABIF'):
        raise RuntimeError("Warning: not an ABIF file")

    t = ABIF()
    t.version = struct.unpack('>h', bdata[4:6])[0]

    dir_entry_size = struct.calcsize(abif_direntry)
    header = struct.unpack(abif_direntry, bdata[6: 6 + dir_entry_size])
    dir_entry_num = header[4]
    dir_entry_off = struct.unpack('>l', header[6])[0]

    # read dir_entry and its associated data

    for i in range(0, dir_entry_num):
        offset = dir_entry_off + 28 * i
        elems = struct.unpack(abif_direntry, bdata[offset: offset + 28])
        de = ABIF_DirEntry(*elems)
        if de.tag in t.dir_entries:
            t.dir_entries[de.tag][de.no] = de
        else:
            t.dir_entries[de.tag] = {de.no: de}

        # alt_type = abitags.get("%s%d" % (de.tag, de.no), de.etype)
        alt_type = abitags.get(de.tag + str(de.no).encode('ASCII'), de.etype)
        if alt_type != de.etype:
            D("Warning: inconsistent element type for %s" % de.tag)
        if alt_type == 18:
            de.num -= 1
        etype_fmt = abitypes.get(alt_type)
        if not etype_fmt:
            raise RuntimeError('unknown alt_type: %d with de.num: %d' %
                               (alt_type, de.num))
        if alt_type not in (10, 11, 1024):
            etype_fmt = etype_fmt % de.num
        elif alt_type == 1024:
            etype_fmt = etype_fmt % (de.esize * de.num)
        # D(etype_fmt, alt_type)
        if de.dsize <= 4:
            de.data = struct.unpack(etype_fmt, de.drec[:de.dsize])
            if alt_type in [10, 11]:
                continue
        else:
            offset = struct.unpack('>l', de.drec)[0]
            buf = bdata[offset: offset + de.dsize]
            # print(de.tag, de.no, de.etype, de.esize, etype_fmt, de.dsize)
            de.data = struct.unpack(etype_fmt, buf)
        if de.num == 1 or alt_type in (18, 19, 2):
            de.data = de.data[0]

    return t


FILTER_SETS = {
    'G5': {
        '6-FAM':    {'filter': 'B', 'rgb': (0, 0, 1)},
        'VIC':      {'filter': 'G', 'rgb': (0, 1, 0)},
        'NED':      {'filter': 'Y', 'rgb': (0.95, 0.95, 0)},
        'PET':      {'filter': 'R', 'rgb': (1, 0.5, 0)},
        'LIZ':      {'filter': 'O', 'rgb': (1, 0, 0)}
    }
}

WAVELENGTH = {
    ''
    '6-FAM': 522,
    'VIC': 554,
    'NED': 575,
    'PET': 595,
    'LIZ': 655,
}

if __name__ == '__main__':
    """ write spectra in abif file to tab-separated text file """
    for infile in argv[1:]:
        with open(infile, 'rb') as instream:
            t = read_abif_stream(instream)
        channels = t.get_channels()
        names = ['"' + c[0] + '"' for c in channels]
        with open(infile + '.txt', 'wt') as out:
            out.write('\t'.join(names))
            out.write('\n')
            for p in zip(* [c[2] for c in channels]):
                out.write('\t'.join(str(x) for x in p))
                out.write('\n')
