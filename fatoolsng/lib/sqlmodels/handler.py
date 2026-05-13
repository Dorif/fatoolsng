from sys import exit as sys_exit
from os.path import isfile
from fatoolsng.lib.utils import cerr
from fatoolsng.lib.sqlmodels.handler_interface import base_sqlhandler
from fatoolsng.lib.sqlmodels import schema


class SQLHandler(base_sqlhandler):

    Panel = schema.Panel
    Marker = schema.Marker
    Batch = schema.Batch
    Sample = schema.Sample
    FSA = schema.FSA
    Channel = schema.Channel
    AlleleSet = schema.AlleleSet
    Allele = schema.Allele

    def __init__(self, dbfile, initial=False):
        cerr(f"Opening db: {dbfile}")
        if not initial and not isfile(dbfile):
            cerr(f'ERR - sqlite db file not found: {dbfile}')
            sys_exit(1)
        if initial and isfile(dbfile):
            cerr(f'ERR - sqlite db file already exists: {dbfile}')
            sys_exit(1)
        self.dbfile = dbfile
        self.engine, self.session = schema.engine_from_file(dbfile)

    def initdb(self, create_table=True):
        if create_table:
            schema.Base.metadata.create_all(self.engine)
        from fatoolsng.lib.sqlmodels.setup import setup
        setup(self)
        cerr(f'Database at {self.dbfile} has been initialized.')
