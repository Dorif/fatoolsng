from fatoolsng.lib.analytics.export import export_demetics
# from fatools.lib.utils import cerr, cout, random_string
from subprocess import call
from collections import defaultdict
# import jax.numpy as np
from datetime import date
from os.path import exists


def run_demetics(analytical_sets, dbh, tmp_dir, mode='d.jost'):

    # demetics output cannot be managed as it directly writes output file
    # to current working directory as such, we need to run demetics under
    # a script that will change the current directory

    script_file = f'{tmp_dir}/demetics.r'
    data_file = f'{tmp_dir}/data.txt'

    with open(data_file, 'w') as dataout:
        export_demetics(analytical_sets, dbh, dataout)

    with open(script_file, 'w') as scriptout:
        scriptout.write(f'setwd("{tmp_dir}")\n'
                        'library(DEMEtics)\n'
                        f'dat <- read.table("{data_file}", header=T)\n'
                        'D.Jost("dat", bias="correct", object=TRUE,format.table=FALSE,pm="pairwise", statistics="CI", bt=1000)\n')

    today = date.today().strftime('%Y-%m-%d')

    # TODO: prepare stdout & stderr
    ok = call(['Rscript', script_file])

    # demetics save its output to files with names AND dates...
    mean_file = f"{tmp_dir}/dat.pairwise.Dest.mean.{today}.txt"
    ci_file = f"{tmp_dir}/dat.pairwise.Dest.mean.ci.{today}.txt"

    d = defaultdict(dict)

    if exists(ci_file):
        with open(ci_file) as infile:
            in_data = False
            for r in infile:
                r = r.strip()
                if not in_data:
                    if r == 'Dest.mean Population1 Population2 Lower.0.95.CI Upper.0.95.CI':
                        in_data = True
                    continue

                cols = r.split()
                d[cols[1]][cols[2]] = f'{float(cols[0]):4.3f}'
                d[cols[2]][cols[1]] = f'{float(cols[3]):6.3f} - {float(cols[4]):6.3f}'

        return dict(M=d, data_file=data_file, msg='')

    if exists(mean_file):
        # just use the mean file
        with open(mean_file) as infile:
            next(infile)    # skip the header
            for r in infile:
                r = r.strip()
                cols = r.split()
                d[cols[1]][cols[2]] = f'{float(cols[0]):4.3f}'
                d[cols[2]][cols[1]] = '-'

        return dict(M=d, data_file=data_file,
                    msg="Bootstrapping process failed."
                    " Please download the data and run DEMEtics locally to inspect the problem.")

    return dict(M=None, data_file=data_file,
                msg="Problem running DEMEtics with this data set."
                " Please download the data and run DEMEtics locally to inspect the problem.")
