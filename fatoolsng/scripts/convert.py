from argparse import ArgumentParser
from csv import DictReader
from collections import defaultdict
from fatoolsng.lib.utils import cerr, cexit, get_dbhandler
from fatoolsng.lib.fautil.traceio import read_abif_stream


def init_argparser(parser=None):

    if parser is None:
        p = ArgumentParser('convert')
    else:
        p = parser

# commands
    p.add_argument('--fsa2tab', default=False, action='store_true',
                   help='convert from FSA to TSV')
    p.add_argument('--genemapper2tab', default=False, action='store_true',
                   help='convert genemapper CSV to fatoolsng assay info TSV')
    p.add_argument('--checkfsa', default=False, action='store_true',
                   help='check FSA files')
# options
    p.add_argument('--sqldb', default=False, help='SQLITE3 database filename')
    p.add_argument('--fsdb', default=False,
                   help='root directory for filesystem-based database')
    p.add_argument('--species', default=False, help='species for markers')
    p.add_argument('--fsadir', default=False,
                   help='root directory for FSA files')
# mandatory options
    p.add_argument('infiles', nargs='+')

    return p


def main(args):
    do_convert(args)


def do_convert(args, dbh=None):

    if not dbh and (args.sqldb or args.fsdb):
        dbh = get_dbhandler(args)

    if args.fsa2tab:
        do_fsa2tab(args)
    elif args.genemapper2tab:
        do_genemapper2tab(args, dbh)
    elif args.checkfsa:
        do_checkfsa(args)
    else:
        cerr('Unknown command, nothing to do!')
        return False
    return True


def do_fsa2tab(args):

    for infile in args.infiles:
        with open(infile, 'rb') as instream:
            t = read_abif_stream(instream)
        channels = t.get_channels()
        names = ['"' + c + '"' for c in channels]
        print(f"Dyes: {' '.join(channels)}")
        with open(infile + '.raw.tab', 'wt') as out:
            out.write('\t'.join(names))
            out.write('\n')
            for p in zip(*[channels[c].raw for c in channels]):
                out.write('\t'.join(str(x) for x in p))
                out.write('\n')
        with open(infile + '.base.tab', 'wt') as out:
            out.write('\t'.join(names))
            out.write('\n')
            for p in zip(*[channels[c].smooth() for c in channels]):
                out.write('\t'.join(str(x) for x in p))
                out.write('\n')


def do_genemapper2tab(args, dbh):

    species = None
    if args.species:
        species = args.species

    for infile in args.infiles:

        sample_set = defaultdict(list)
        with open(infile) as csv_fh:
            csv_in = DictReader(csv_fh)
            assay_list = {}

            for row in csv_in:
                assay = row['Sample File']
                sample = row['Sample Name']
                run_name = row['Run Name']
                panel = row['Panel']
                marker = row['Marker']

                if assay in assay_list:
                    if assay_list[assay] != run_name:
                        cexit(f'Inconsistence or duplicate FSA file name: {assay}')
                else:
                    assay_list[assay] = run_name

                token = (sample, assay, panel)
                sample_set[token].append(marker)

        with open(infile + '.tab', 'w') as outfile:
            outfile.write('SAMPLE\tASSAY\tPANEL\tOPTIONS\n')

            for token in sorted(sample_set.keys()):
                sample, assay, panel = token
                markers = sample_set[token]

                db_panel = dbh.get_panel(panel)
                s_panel_markers = set(x.upper()
                                      for x in db_panel.get_marker_codes())
                s_assay_markers = set((f'{species}/{x}'
                                       if (species and '/' not in x)
                                       else x).upper()
                                      for x in markers)

                excludes = s_panel_markers - s_assay_markers
                if s_assay_markers - s_panel_markers:
                    cexit(f'ERROR inconsistent marker(s) for sample {sample} assay {assay}: {str(s_assay_markers-s_panel_markers)}')

                if excludes:
                    excludes = f"exclude={','.join(excludes)}"
                else:
                    excludes = ''

                outfile.write(f'{sample}\t{assay}\t{panel}\t{excludes}\n')


def do_checkfsa(args):

    fsadir = args.fsadir or '.'

    for infile in args.infiles:
        with open(infile) as csv_fh:
            data = DictReader(csv_fh, delimiter='\t')

            files = {}
            line = 2
            for row in data:
                sample = row['SAMPLE']
                if sample.startswith('#'):
                    line += 1
                    continue
                assay_file = row['ASSAY']
                panel = row['PANEL']
                if assay_file in files:
                    cerr(f'WARN file: {infile} - duplicated assay: {assay_file} for sample {sample} panel {panel}')
                files[assay_file] = True
                try:
                    with open(f'{fsadir}/{assay_file}', 'rb') as instream:
                        t = read_abif_stream(instream)
                    line += 1
                except:
                    cerr(f'ERR file: {infile} line: {line}  - sample: {sample} assay: {assay_file}')
                    # raise
                    line += 1
