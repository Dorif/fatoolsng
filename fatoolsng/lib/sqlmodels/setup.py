from fatoolsng.lib.utils import cerr
from fatoolsng.lib.params import default_markers, default_panels


def setup(dbh):

    session = dbh.session()

    # create default markers
    for d in default_markers.values():
        marker = dbh.new_marker()
        marker.update(d)
        marker.remark = f'Test __slots__ for {marker.code}!'
        marker.anything = 'abc'
        cerr(f"I: marker '{marker.code}' created.")
        session.add(marker)

    # create default panels
    for d in default_panels.values():
        panel = dbh.new_panel()
        panel.update(d)
        cerr(f"I: panel '{panel.code}' created.")
        session.add(panel)

    # create default batch (for bin holder)
    batch = dbh.Batch(code='default')
    batch.fsa_provider = ''
    batch.species = 'X'
    cerr("I: batch 'default' created.")
    session.add(batch)
