from sys import exit as sys_exit, stdout
from argparse import ArgumentParser
from transaction import manager as transaction_manager
from fatoolsng.lib.utils import cout, cerr, cexit, get_dbhandler, set_verbosity
from fatoolsng.lib import params
from fatoolsng.lib.const import assaystatus, peaktype
from fatoolsng.lib.fautil import algo


def init_argparser(parser=None):

    if parser:
        p = parser
    else:
        p = ArgumentParser('facmd')

    p.add_argument('--sqldb', default=False, help='SQLite3 database filename')

    p.add_argument('--fsdb', default=False,
                   help='directory for filesystem-based database')

    p.add_argument('--clear', default=False, action='store_true',
                   help='clear / remove all peaks from assay')

    p.add_argument('--scan', default=False, action='store_true',
                   help='scanning assay for peaks')

    p.add_argument('--preannotate', default=False, action='store_true',
                   help='preannotate assay for overlapping peaks, stutter and broad peaks')

    p.add_argument('--alignladder', default=False, action='store_true',
                   help='align ladder peaks with standard size')

    p.add_argument('--call', default=False, action='store_true',
                   help='calling peaks (determining the sizes of peaks)')

    p.add_argument('--bin', default=False, action='store_true',
                   help='binning peaks')

    p.add_argument('--postannotate', default=False, action='store_true',
                   help='post annotate peaks')

    p.add_argument('--listpeaks', default=False, action='store_true',
                   help='list all peaks')

    p.add_argument('--listassay', default=False, action='store_true',
                   help='list assay information')

    p.add_argument('--showtrace', default=False, action='store_true',
                   help='show trace as a plot')

    p.add_argument('--findpeaks', default=False, action='store_true',
                   help='only find peaks')

    p.add_argument('--setallele', default=False, action='store_true',
                   help='set allele type')

    p.add_argument('--batch', default=False, help='batch code')

    p.add_argument('--sample', default=False, help='sample code')

    p.add_argument('--assay', default=False, help='assay filename')

    p.add_argument('--marker', default=False, help='marker code')

    p.add_argument('--panel', default='', help='panel list (comma separated)')

    p.add_argument('--commit', default=False, action='store_true',
                   help='commit to database')

    p.add_argument('--outfmt', default='text',
                   help='output format, either text or tab')

    p.add_argument('--outfile', default='-', help='output filename')

    p.add_argument('--peakcachedb', default=False,
                   help='peak cache db filename')

    p.add_argument('--method', default='',
                   help='spesific method or algorithm to use')

    p.add_argument('--value', default='', help='bin value of alleles')

    p.add_argument('--totype', default='', help='new type of alleles')

    p.add_argument('--fromtype', default='', help='original type of alleles')

    p.add_argument('--excluded_peaks')

    p.add_argument('--stutter_ratio', default=0, type=float)

    p.add_argument('--stutter_range', default=0, type=float)

    p.add_argument('--force', default=False, action='store_true',
                   help='force the method (even if need short-cutting)')

    p.add_argument('--test', default=False, action='store_true',
                   help='just testing, not need to commit to database')

    p.add_argument('-y', default=False, action='store_true',
                   help='say yes to all interactive questions')

    p.add_argument('--abort', default=False, action='store_true',
                   help='abort for any warning')

    p.add_argument('--showladderpca', default=False, action='store_true',
                   help='show PCA plot for ladder peaks')

    p.add_argument('--showz', default=False, action='store_true',
                   help='show Z plot for ladder peaks')

    p.add_argument('--verbose', default=0, type=int,
                   help='show verbositiy of the processing')

    return p


def main(args):

    if args.commit:
        with transaction_manager:
            do_facmd(args)
            cerr('** COMMIT to database **')
    else:
        cerr('WARNING ** running without database COMMIT! All changes will be discarded!')
        if not (args.test or args.y):
            keys = input('Do you want to continue [y/n]? ')
            if not keys.lower().strip().startswith('y'):
                sys_exit(1)
        do_facmd(args)


def do_facmd(args, dbh=None):

    if dbh is None:
        dbh = get_dbhandler(args)

    if args.verbose:
        set_verbosity(args.verbose)

    executed = 0
    args_arr = [args.clear, args.findpeaks, args.scan, args.preannotate,
                args.alignladder, args.call, args.bin, args.postannotate,
                args.setallele, args.showladderpca, args.listassay,
                args.listpeaks, args.showtrace, args.showz]
    do_arr = [do_clear(args, dbh), do_findpeaks(args, dbh), do_scan(args, dbh),
              do_preannotate(args, dbh), do_alignladder(args, dbh),
              do_call(args, dbh), do_bin(args, dbh),
              do_postannotate(args, dbh), do_setallele(args, dbh),
              do_showladderpca(args, dbh), do_listassay(args, dbh),
              do_listpeaks(args, dbh), do_showtrace(args, dbh),
              do_showz(args, dbh)]
    for i in range(14):  # 14 members in arrays above
        if args_arr[i] is not False:
            do_arr[i]
            executed += 1
    if executed:
        cerr(f'INFO - executed {executed} command(s)')
    else:
        cerr('WARN - unknown command, nothing to do!')


def do_clear(args, dbh):

    cerr('Clearing peaks...')

    assay_list = get_assay_list(args, dbh)
    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'Clearing sample: {sample_code} assay {assay.filename} [{counter}/{len(assay_list)}]')

        assay.clear()
        counter += 1


def do_scan(args, dbh):

    cerr('I: Scanning peaks...')

    scanning_parameter = params.Params()
    assay_list = get_assay_list(args, dbh)

    if args.peakcachedb:
        from plyvel import DB
        peakdb = DB(args.peakcachedb, create_if_missing=False)
    else:
        peakdb = None

    if args.method:
        scanning_parameter.ladder.method = args.method
        scanning_parameter.nonladder.method = args.method

    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'I: [{counter}/{len(assay_list)}] - Scanning: {sample_code} | {assay.filename}')

        assay.scan(scanning_parameter, peakdb=peakdb)
        counter += 1


def do_preannotate(args, dbh):

    cerr('I: Preannotating peaks...')

    scanning_parameter = params.Params()
    assay_list = get_assay_list(args, dbh)

    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'I: [{counter}/{len(assay_list)}] - Preannotating: {sample_code} | {assay.filename}')

        assay.preannotate(scanning_parameter)
        counter += 1


def do_alignladder(args, dbh):

    cerr('Aligning ladders...')

    assay_list = get_assay_list(args, dbh)
    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'I: [{counter}/{len(assay_list)}] - Aligning: {sample_code} | {assay.filename}')
        (dpscore, rss, no_of_peaks, no_of_ladders, qcscore, remarks,
         method) = assay.alignladder(args.excluded_peaks,
                                     force_mode=args.force)
        if qcscore < 0.9:
            msg = 'W! low ladder QC'
        else:
            msg = 'I:'
        cerr(f'{msg} [{counter}/{len(assay_list)}] - Score {qcscore:3.2f} {dpscore:4.2f} {rss:5.2f} {no_of_peaks}/{no_of_ladders} {method} for {sample_code} | {assay.filename}')
        if remarks:
            cerr(f"{msg} - {' | '.join(remarks)}")
        if qcscore != 1.0 and args.abort:
            sys_exit(1)

        counter += 1


def do_call(args, dbh):

    cerr('I: Calling peaks...')

    scanning_parameter = params.Params()

    assay_list = get_assay_list(args, dbh)
    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'I: [{counter}/{len(assay_list)}] - Calling: {sample_code} | {assay.filename}')
        assay.call(scanning_parameter)
        counter += 1


def do_bin(args, dbh):

    cerr('I: Binning peaks...')

    scanning_parameter = params.Params()

    if args.marker:
        markers = [dbh.get_marker(code) for code in args.marker.split(',')]
    else:
        markers = None

    assay_list = get_assay_list(args, dbh)
    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'I: [{counter}/{len(assay_list)}] - Binning: {sample_code} | {assay.filename}')
        assay.bin(scanning_parameter, markers)
        counter += 1


def do_postannotate(args, dbh):

    cerr('I: Post-annotating peaks...')

    scanning_parameter = params.Params()

    if args.marker:
        markers = [dbh.get_marker(code) for code in args.marker.split(',')]
    else:
        markers = None

    if args.stutter_ratio > 0:
        scanning_parameter.nonladder.stutter_ratio = args.stutter_ratio
    if args.stutter_range > 0:
        scanning_parameter.nonladder.stutter_range = args.stutter_range

    assay_list = get_assay_list(args, dbh)
    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'I: [{counter}/{len(assay_list)}] - Post-annotating: {sample_code} | {assay.filename}')
        assay.postannotate(scanning_parameter, markers)
        counter += 1


def do_findpeaks(args, dbh):

    from plyvel import DB
    from fatoolsng.lib import params

    cerr('Finding and caching peaks...')

    if not args.peakcachedb:
        cexit('ERR - please provide cache db filename')

    # opening LevelDB database
    if args.peakcachedb == '-':
        peakdb = None
    else:
        peakdb = DB(args.peakcachedb)

    scanning_parameter = params.Params()
    assay_list = get_assay_list(args, dbh)

    if args.method:
        scanning_parameter.ladder.method = args.method
        scanning_parameter.nonladder.method = args.method

    channel_list = []
    counter = 1
    cerr('', nl=False)
    for (assay, sample_code) in assay_list:
        cerr(f'\rI: [{counter}/{len(assay_list)}] processing assay',
             nl=False)
        for c in assay.channels:
            if c.marker.code == 'ladder':
                params = scanning_parameter.ladder
            else:
                params = scanning_parameter.nonladder
            channel_list.append((c.tag(), c.data, params))
        counter += 1
    cerr('')

    do_parallel_find_peaks(channel_list, peakdb)

    # peakdb.close()


def do_setallele(args, dbh):

    marker_codes = args.marker.split(',')
    marker_ids = [dbh.get_marker(code).id for code in marker_codes]
    bin_values = [int(x) for x in args.value.split(',')]

    totype = getattr(peaktype, args.totype)

    assay_list = get_assay_list(args, dbh)
    for (assay, sample_code) in assay_list:
        for c in assay.channels:
            if marker_ids and c.marker_id in marker_ids:
                for allele in c.alleles:
                    if (allele.bin not in bin_values or
                        (args.fromtype and allele.type != args.fromtype)):
                        continue
                    allele.type = totype
                    cerr(f'I: - setting allele {allele.bin} marker {c.marker.label} for sample {sample_code}')


def do_showladderpca(args, dbh):

    assay_list = get_assay_list(args, dbh)
    counter = 1
    for (assay, sample_code) in assay_list:
        cerr(f'Showing ladder PCA for  sample: {sample_code} assay {assay.filename} [{counter}/{len(assay_list)}]')
        assay.showladderpca()


def chk_out(outfile):
    if outfile != '-':
        return open(outfile, 'w')
    else:
        return stdout


def do_listassay(args, dbh):

    assay_list = get_assay_list(args, dbh)

    out_stream = chk_out(args.outfile)
    for (assay, sample_code) in assay_list:
        printout_assay(assay, outfile=out_stream, fmt=args.outfmt)


def do_listpeaks(args, dbh):

    assay_list = get_assay_list(args, dbh)
    if args.marker:
        markers = [dbh.get_marker(code) for code in args.marker.split(',')]
    else:
        markers = None

    if markers:
        cerr(f"Markers: {','.join(m.code for m in markers)}")

    out_stream = chk_out(args.outfile)
    out_stream.write('SAMPLE\tFILENAME\tDYE\tRTIME\tHEIGHT\tSIZE\tSCORE\tID\n')

    for (assay, sample_code) in assay_list:
        cout(f'Sample: {sample_code} assay: {assay.filename}')
        for channel in assay.channels:
            if markers and channel.marker not in markers:
                continue
            cout(f'Marker => {channel.marker.code} | {channel.dye} [{len(channel.alleles)}]')
            for p in channel.alleles:
                out_stream.write(f'{sample_code}\t{assay.filename}\t{channel.dye}\t{p.rtime:d}\t{p.height:d}\t{p.size:5.3f}\t{p.qscore:3.2f}\t{p.id:d}\n')


def do_showtrace(args, dbh):

    assay_list = get_assay_list(args, dbh)

    from matplotlib import pylab as plt

    for (assay, sample_code) in assay_list:
        peaks = []
        for c in assay.channels:
            plt.plot(c.raw_data)
            peaks += list(c.alleles)

        for p in peaks:
            plt.plot(p.rtime, p.height, 'r+')

        plt.show()


def do_showz(args, dbh):

    assay_list = get_assay_list(args, dbh)

    from matplotlib import pylab as plt
    from numpy import poly1d
    from jax.numpy import linspace

    for (assay, sample_code) in assay_list:
        ladder_peaks = list(assay.ladder.alleles)
        z = assay.z

        peak_pairs = [(x.rtime, x.size) for x in ladder_peaks]

        x = linspace(peak_pairs[0][0], peak_pairs[-1][0] + 200, 100)
        f = poly1d(z)
        y = f(x)

        print(' => Z: ', z)
        for p in ladder_peaks:
            print(f' => {p.rtime:6d} -> {f(p.rtime):6.2f} | {p.size:4d} | {abs(f(p.rtime)-p.size):5.2f}')

        plt.plot(x, y)
        rtimes = [x[0] for x in peak_pairs]
        sizes = [x[1] for x in peak_pairs]
        plt.scatter(rtimes, sizes)
        plt.show()

# helpers


def get_assay_list(args, dbh):

    if not args.batch:
        cerr('ERR - need --batch argument!')
        sys_exit(1)

    batch = dbh.get_batch(args.batch)
    if not batch:
        cerr(f'ERR - batch {args.batch} not found!')
        sys_exit(1)

    samples = []
    if args.sample:
        samples = args.sample.split(',')

    assays = []
    if args.assay:
        assays = args.assay.split(',')

    panels = []
    if args.panel:
        panels = args.panel.split(',')

    assay_list = []
    for sample in batch.samples:
        if samples and sample.code not in samples:
            continue
        for assay in sample.assays:
            if ((assays and assay.filename not in assays) or
                (panels and assay.panel.code not in panels)):
                continue
            assay_list.append((assay, sample.code))

    cerr(f'INFO - number of assays to be processed: {len(assay_list)}')
    return assay_list


# PRINTOUT

def printout_assay(assay, outfile=stdout, fmt='text'):

    if fmt == 'tab':
        outfile.write(f'{assay.sample.code}\t{assay.filename}\t{assay.score:f}\t{assay.dp:f}\t{assay.rss:f}\t{assay.ladder_peaks:d}\t{len(assay.ladder.alleles):d}\t{assay.method}\n')
        return ''

    buf = []
    _ = buf.append

    _(f'Assay: {assay.filename} -- Sample: {assay.sample.code}')
    if assay.status in (assaystatus.aligned, assaystatus.called,
                        assaystatus.annotated, assaystatus.binned):
        _(f' => Score: {assay.score:3.2f}, DP: {assay.dp:5.2f}, RSS: {assay.rss:5.2f}, N-peak: {assay.ladder_peaks}')

    return '\n'.join(buf)


# parallel word

def do_parallel_find_peaks(channel_list, peakdb):

    import concurrent.futures
    from pickle import dumps as pickle_dumps

    cerr('I: Processing channel(s)')
    total = len(channel_list)
    counter = 0
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for (tag, peaks) in executor.map(find_peaks_p, channel_list):
            if peakdb:
                peakdb.put(tag.encode(), pickle_dumps(peaks))
            else:
                cout(f'== channel {tag}\n')
                cout(str(peaks))
            counter += 1
            cerr(f'I: [{counter}/{total}] channel {tag} => {len(peaks)} peak(s)')


def find_peaks_p(args):
    tag, data, param = args

    return (tag, algo.find_raw_peaks(data, param))
