# pair minimization algorithm
from numpy import poly1d
from itertools import product
from jax.scipy.optimize import minimize
from fatoolsng.lib.utils import cverr, is_verbosity
from fatoolsng.lib.fautil.alignutils import (estimate_z, pair_f, align_dp,
                                             pair_sized_peaks, DPResult,
                                             AlignResult, plot)
from fatoolsng.lib.fautil.gmalign import ZFunc, align_gm
from fatoolsng.lib import const

ANCHOR_RTIME_LOWER_BOUND = 1400
ANCHOR_RTIME_UPPER_BOUND = 5000
PEAK_RTIME_UPPER_BOUND = 11000


def align_pm(peaks, ladder, anchor_pairs=None):

    if not anchor_pairs:
        longest_rtime_peak = max([p.rtime for p in peaks])
        if longest_rtime_peak > PEAK_RTIME_UPPER_BOUND:
            bound_adjust_ratio = longest_rtime_peak / PEAK_RTIME_UPPER_BOUND
            anchor_start = ANCHOR_RTIME_LOWER_BOUND * bound_adjust_ratio
            anchor_end = ANCHOR_RTIME_UPPER_BOUND * bound_adjust_ratio
        else:
            anchor_start = ANCHOR_RTIME_LOWER_BOUND
            anchor_end = ANCHOR_RTIME_UPPER_BOUND
        anchor_peaks = [p for p in peaks if anchor_start < p.rtime < anchor_end]
        anchor_pairs, initial_z = estimate_pm(anchor_peaks,
                                              ladder['signature'])

    else:
        rtimes, bpsizes = zip(*anchor_pairs)
        initial_z = estimate_z(rtimes, bpsizes, 1)

    anchor_pairs.sort()
    pairs, z, rss, f = align_upper_pm(peaks, ladder, anchor_pairs, initial_z)
    pairs, z, rss, f = align_lower_pm(peaks, ladder, pairs, initial_z)

    # last dp
    dp_result = align_dp(f.rtimes, f.sizes, f.similarity, z, rss)
    if is_verbosity(1):
        print(dp_result.sized_peaks)
    if is_verbosity(4):
        plot(f.rtimes, f.sizes, dp_result.z,
             [(x[1], x[0]) for x in dp_result.sized_peaks])

    dp_result.sized_peaks = f.get_sized_peaks(dp_result.sized_peaks)

    score, msg = ladder['qcfunc'](dp_result, method='strict')
    if score > 0.9:
        return AlignResult(score, msg, dp_result, const.alignmethod.pm_strict)

    score, msg = ladder['qcfunc'](dp_result, method='relax')
    return AlignResult(score, msg, dp_result, const.alignmethod.pm_relax)


def align_lower_pm(peaks, ladder, anchor_pairs, anchor_z):

    # this is another attempt to perform ladder - size standard alignment one peak by one

    anchor_pairs = sorted(anchor_pairs)
    anchor_rtimes, anchor_bpsizes = zip(*anchor_pairs)
    anchor_rtimes = list(anchor_rtimes)
    anchor_bpsizes = list(anchor_bpsizes)
    remaining_sizes = [x for x in ladder['sizes'] if x < anchor_bpsizes[0]]
    current_sizes = anchor_bpsizes
    zscore = estimate_z(anchor_rtimes, anchor_bpsizes, 3)
    z = zscore.z
    rss = zscore.rss
    f = ZFunc(peaks, current_sizes, anchor_pairs)

    while True:

        if not remaining_sizes:
            return pairs, z, rss, f

        current_sizes.insert(0, remaining_sizes.pop(-1))
        f.set_sizes(current_sizes)
        score, next_z = minimize_score(f, z, 3)
        next_pairs, next_rss = f.get_pairs(next_z)

        # if delta rss (current rss - prev rss) is above certain threshold,
        # then assume the latest peak standar is not appropriate, and
        # use previous z and rss
        if (next_rss - rss) > 20:
            current_sizes.pop(0)
        else:
            z = next_z
            rss = next_rss
            pairs = next_pairs

        if is_verbosity(5):
            plot(f.rtimes, f.sizes, z, pairs)


def align_upper_pm(peaks, ladder, anchor_pairs, anchor_z):

    # this is another attempt to perform ladder - size standard alignment one peak by one

    anchor_pairs = sorted(anchor_pairs)
    anchor_rtimes, anchor_bpsizes = zip(*anchor_pairs)
    anchor_rtimes = list(anchor_rtimes)
    anchor_bpsizes = list(anchor_bpsizes)
    remaining_sizes = [x for x in ladder['sizes'] if x > anchor_bpsizes[-1]]
    current_sizes = anchor_bpsizes
    order = ladder['order']
    zres = estimate_z(anchor_rtimes, anchor_bpsizes, order)
    z, rss = zres.z, zres.rss
    f = ZFunc(peaks, current_sizes, anchor_pairs)

    while remaining_sizes:

        current_sizes.append(remaining_sizes.pop(0))
        if (remaining_sizes and
            (remaining_sizes[-1] - current_sizes[-1]) < 100 and
            (remaining_sizes[0] - current_sizes[-1]) < 11):
            current_sizes.append(remaining_sizes.pop(0))

        f.set_sizes(current_sizes)
        score, next_z = minimize_score(f, z, order)
        next_pairs, next_rss = f.get_pairs(z)

        if (next_rss - rss) < 70:
            z = next_z
            rss = next_rss
            pairs = next_pairs

        if is_verbosity(5):
            plot(f.rtimes, f.sizes, z, pairs)

    # finalize the alignment with stringent criteria
    dp_result = align_dp(f.rtimes, f.sizes, f.similarity, z, rss)
    if dp_result.rss - rss > 50:
        return pairs, z, rss, f
    dp_pairs = [(x[1], x[0]) for x in dp_result.sized_peaks]
    if is_verbosity(5):
        plot(f.rtimes, f.sizes, dp_result.z, dp_pairs)

    return dp_pairs, dp_result.z, dp_result.rss, f


def minimize_score(f, z, order):

    last_score = score = 0

    niter = 1
    while niter < 50:

        score = f(z)

        if last_score and abs(last_score - score) < 1e-6:
            break

        pairs, rss = f.get_pairs(z)
        rtimes, bpsizes = zip(*pairs)
        zres = estimate_z(rtimes, bpsizes, order)

        z = zres.z
        last_score = score
        niter += 1

    return last_score, z


def estimate_pm(peaks, bpsizes):

    rtimes = [p.rtime for p in peaks]

    rtime_points = prepare_rtimes(rtimes)
    bpsize_pair = [bpsizes[1], bpsizes[-2]]

    f = ZFunc(peaks, bpsizes, [], estimate=True)

    scores = []
    for rtime_pair in rtime_points:
        if rtime_pair[0] >= rtime_pair[1]:
            continue

        # y = ax + b
        # y1 = ax1 + b
        # y2 = ax2 + b
        # ------------ -
        # y1 - y2 = a(x1 - x2)
        # a = (y1 - y2)/(x1 - x2)
        # b = y1 - ax1

        # slope = (bpsize_pair[1]-bpsize_pair[0]) / (rtime_pair[1]-rtime_pair[0])
        # intercept = bpsize_pair[0] - slope * rtime_pair[0]
        # z = [slope intercept]
        zres = estimate_z(rtime_pair, bpsize_pair, 1)
        score = f(zres.z)
        scores.append((score, zres))
        if is_verbosity(5):
            plot(f.rtimes, f.sizes, zres.z, [])

    scores.sort(key=lambda x: x[0])
    zresult = scores[0][1]

    dp_result = align_dp(f.rtimes, f.sizes, f.similarity, zresult.z,
                         zresult.rss)
    if is_verbosity(5):
        plot(f.rtimes, f.sizes, dp_result.z,
             [(x[1], x[0]) for x in dp_result.sized_peaks])

    return ([(x[1], x[0]) for x in dp_result.sized_peaks], dp_result.z)


def prepare_rtimes(rtimes):
    # prepare combination of begin and end rtimes

    mid_size = round(len(rtimes)/2)
    return list(product(rtimes[:mid_size], rtimes[mid_size-2:]))
