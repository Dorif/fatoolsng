"""ABIF/FSA file reader — Biopython-backed, instrument-agnostic.

Replaces the original hand-rolled struct parser with Bio.SeqIO.AbiIO,
which handles all ABIF data types and all instruments (ABI 3500/3730,
SeqStudio, SeqStudio Flex, RapidHIT, Promega CE, third-party clones).

Public interface is unchanged: read_abif_stream() → ABIF, with
ABIF.get_channels() and ABIF.get_run_start_time().
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import BinaryIO

from Bio.SeqIO import read as bio_read
from jax.numpy import array
from numpy.typing import NDArray

from fatoolsng.lib.fautil.traceutils import smooth_signal, correct_baseline


# Fallback wavelengths when DyeW tags are absent from the file.
WAVELENGTH = {
    '6-FAM': 522,
    'VIC':   554,
    'NED':   575,
    'PET':   595,
    'LIZ':   655,
}

FILTER_SETS = {
    'G5': {
        '6-FAM': {'filter': 'B', 'rgb': (0,    0,    1)},
        'VIC':   {'filter': 'G', 'rgb': (0,    1,    0)},
        'NED':   {'filter': 'Y', 'rgb': (0.95, 0.95, 0)},
        'PET':   {'filter': 'R', 'rgb': (1,    0.5,  0)},
        'LIZ':   {'filter': 'O', 'rgb': (1,    0,    0)},
    }
}

# Non-standard dye names written by various instruments.
_DYE_ALIASES = {
    '6FAM':    '6-FAM',
    'FAM':     '6-FAM',
    'PAT':     'PET',
    'Bn Joda': 'LIZ',
    'ROX':     'LIZ',   # some Chinese instruments label LIZ channel as ROX
}


def _decode_dye(raw: str | bytes) -> str:
    """Decode a bytes dye name, strip nulls/whitespace, apply alias map."""
    if isinstance(raw, bytes):
        raw = raw.decode('ascii', errors='replace')
    name = raw.strip('\x00').strip()
    return _DYE_ALIASES.get(name, name)


class ABIF_Channel:
    """One fluorescence channel from an FSA file."""

    def __init__(self, dye_name: str, wavelength: int, trace: NDArray) -> None:
        self.dye_name  = dye_name
        self.wavelength = wavelength
        self.raw       = trace
        self._smooth: NDArray | None = None

    def smooth(self) -> NDArray:
        """Return baseline-corrected Savitzky-Golay smoothed trace (cached)."""
        if self._smooth is None:
            self._smooth = correct_baseline(smooth_signal(self.raw))
        return self._smooth


class ABIF:
    """Thin wrapper around Biopython's abif_raw tag dictionary."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw  # dict: tag+number → parsed value

    # ------------------------------------------------------------------

    def get_channels(self) -> dict[str, ABIF_Channel]:
        """Return {dye_name: ABIF_Channel} for all readable channels."""
        raw = self._raw
        results: dict[str, ABIF_Channel] = {}

        # Each physical channel has a DyeN index; raw signal is in DATA1-4
        # (or DATA105 for the 5th channel on some ABI instruments).
        # Newer instruments sometimes only write processed DATA9-12 instead
        # of raw DATA1-4 — fall back to those when raw channels are absent.
        channel_slots = [
            (1, [1,   9]),
            (2, [2,  10]),
            (3, [3,  11]),
            (4, [4,  12]),
            (5, [105]),
        ]

        for idx, data_candidates in channel_slots:
            dye_raw = raw.get(f'DyeN{idx}')
            if dye_raw is None:
                continue

            dye_name = _decode_dye(dye_raw)
            if not dye_name:
                continue

            trace_data = None
            for data_idx in data_candidates:
                trace_data = raw.get(f'DATA{data_idx}')
                if trace_data is not None:
                    break
            if trace_data is None:
                continue

            wav_raw = raw.get(f'DyeW{idx}')
            wavelength = int(wav_raw) if wav_raw is not None \
                else WAVELENGTH.get(dye_name, 0)

            results[dye_name] = ABIF_Channel(dye_name, wavelength,
                                             array(trace_data))
        return results

    def get_run_start_time(self) -> datetime:
        """Return run start as a datetime object."""
        date_str = self._raw.get('RUND1', '1970-01-01')
        time_str = self._raw.get('RUNT1', '00:00:00')
        return datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M:%S')


# ------------------------------------------------------------------
# Public entry point

def read_abif_stream(istream: BinaryIO) -> ABIF:
    """Parse an ABIF/FSA stream and return an ABIF object.

    Accepts any binary stream (file handle, BytesIO, etc.).
    Raises RuntimeError if the stream is not a valid ABIF file.
    """
    data = istream.read()
    if not data.startswith(b'ABIF'):
        raise RuntimeError('Not a valid ABIF file')
    record = bio_read(BytesIO(data), 'abi')
    return ABIF(record.annotations['abif_raw'])
