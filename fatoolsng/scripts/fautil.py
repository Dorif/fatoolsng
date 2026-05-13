from argparse import ArgumentParser
from pathlib import Path
from fatoolsng.lib.utils import cout, cerr, cexit


def init_argparser():

    p = ArgumentParser('fautil')

    p.add_argument('--info', default=False, action='store_true',
                   help='get information on FA assay')

    p.add_argument('--view', default=False, action='store_true',
                   help='view information')

    p.add_argument('--analyze', default=False, action='store_true',
                   help='analyze single FSA file')

    p.add_argument('--file', default=False, help='input file')

    p.add_argument('--sqldb', default=False, help='Sqlite database file')

    p.add_argument('--sizestandard', default='LIZ600', help='Size standard')

    return p


cache_traces = {}


def main(args):

    do_fautil(args)


def do_fautil(args):

    if args.sqldb:
        dbh = get_dbhandler(args)
    else:
        dbh = None
    if args.info is not False:
        do_info(args, dbh)
    if args.view is not False:
        do_view(args, dbh)
    if args.analyze is not False:
        do_analyze(args)


def get_traces(args, dbh):

    traces = []

    if dbh is None:
        # get from infile
        infile = args.file
        if infile is False:
            cexit('E - Please provide a filename or Sqlite database path')
        fsa_path = Path(args.file).resolve()
        if fsa_path in cache_traces:
            traces.append((fsa_path, cache_traces[fsa_path]))
        else:
            from fatoolsng.lib.fautil.traceio import read_abif_stream
            with fsa_path.open('rb') as instream:
                t = read_abif_stream(instream)
                cache_traces[fsa_path] = t
                traces.append((fsa_path, t))
    else:
        pass
    return traces


def do_info(args, dbh):

    traces = get_traces(args, dbh)

    for fsa_path, trace in traces:
        cout(f'I - trace: {fsa_path}')
        cout(f'I - runtime: {trace.get_run_start_time()}')


def do_view(args, dbh):
    traces = get_traces(args, dbh)

    from fatoolsng.lib.gui.viewer import viewer
    for fsa_path, trace in traces:
        viewer(trace)


def do_analyze(args):
    """ open a tracefile, performs fragment analysis (scan & call only)
    """

    from fatoolsng.lib.fautil.traceio import read_abif_stream
#    from fatoolsng.lib.fautil.traceutils import separate_channels
    from fatoolsng.lib.fileio.models import FSA as Assay, Marker, Panel
    from fatoolsng.lib import params

    scanning_parameter = params.Params()
    # create dummy markers
    ladder = Marker('ladder', 10, 600, 0, None)
    # create dummy panel
    dummy_panel = Panel('-', {'ladder': args.sizestandard,
                              'markers': {}, })
    with open(args.file, 'rb') as in_stream:
        cerr(f'Reading FSA file: {args.file}')
        t = read_abif_stream(in_stream)
    # create a new Assay and add trace
    assay = Assay()
    assay.size_standard = args.sizestandard
    assay._trace = t
    # create all channels
    assay.create_channels()
    # assign all channels
    assay.assign_channels(panel=dummy_panel)
# scan for peaks
    assay.scan(scanning_parameter)
# scan all channels
