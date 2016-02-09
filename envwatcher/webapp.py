import os
import sys
import time
import subprocess
from textwrap import dedent

from flask import Flask, render_template, abort, send_file, request


import matplotlib
matplotlib.use('agg')  # non-interactive backend
from .plots import write_series_plots

from .utils import check_for_recorder

DATASETS_DIR = 'datasets'
PLOTS_DIR = 'plots'
PROGRESS_NAME = 'recorder_progress'
DEG_F = False
ALWAYS_MAKE_PLOTS_AT_SERIES_REQUEST = False

app = Flask(__name__.split('.')[0])
app.config.from_object(__name__)


@app.before_first_request
def before_first():
    dsetdir = os.path.join(app.root_path, app.config['DATASETS_DIR'])
    plotsdir = os.path.join(app.root_path, app.config['PLOTS_DIR'])
    if not os.path.exists(dsetdir):
        os.mkdir(dsetdir)
    if not os.path.exists(plotsdir):
        os.mkdir(plotsdir)


@app.route("/")
@app.route("/index")
def index():
    series = []
    dsetdir = os.path.join(app.root_path, app.config['DATASETS_DIR'])
    recorder_fn = os.path.join(dsetdir, app.config['PROGRESS_NAME'])

    recorder_info = {}
    recorder_present = check_for_recorder(recorder_fn, recorder_info)
    if 'Output(s)' in recorder_info:
        for entry in recorder_info['Output(s)'].split(','):
            if entry.endswith('_cal'):
                recorder_info['series_name'] = os.path.split(entry)[-1][:-4]


    if os.path.isdir(dsetdir):
        dsls = os.listdir(dsetdir)
        for fn in dsls:
            if fn.endswith('_cal'):
                series.append(fn[:-4])

    return render_template('index.html',
                           series=series,
                           recorder_present=recorder_present,
                           recorder_info=recorder_info)


@app.route("/series/<series_name>")
def series(series_name):
    dsetdir = os.path.join(app.root_path, app.config['DATASETS_DIR'])
    progressfn = os.path.join(dsetdir, app.config['PROGRESS_NAME'])
    infodct = {}
    recorder_present = check_for_recorder(progressfn, infodct)

    if app.config['ALWAYS_MAKE_PLOTS_AT_SERIES_REQUEST'] or not recorder_present:
        dsetfn = os.path.join(dsetdir, series_name + '_cal')
        plotsdir = os.path.join(app.root_path, app.config['PLOTS_DIR'])
        plot_names = write_series_plots(dsetfn, plotsdir, app.config['DEG_F'])
    else:
        plot_names = [pair.split('|') for pair in infodct['Plot names'].split(', ')]

    plots = [dict(name=nm, path='/plots/{}?{}'.format(path,time.time()))
             for nm, path in plot_names]
    return render_template('series.html', series_name=series_name, plots=plots)


@app.route("/plots/<plotid>")
def plots(plotid):
    if plotid.startswith('..') or plotid.startswith('/'):
        abort(404)
    plotfn = os.path.join(app.root_path, app.config['PLOTS_DIR'], plotid)
    return send_file(plotfn)


@app.route("/start_recorder", methods=['POST'])
def start_recorder():
    dsetdir = os.path.join(app.root_path, app.config['DATASETS_DIR'])

    progressfn = os.path.join(dsetdir, app.config['PROGRESS_NAME'])
    if check_for_recorder(progressfn):
        raise IOError('Progress file for recorder "{}" present.  Cannot start '
                      'new recorder until it is cleared.'.format(progressfn))

    series_name = request.form['series']
    waittime = int(request.form['sampletime'])

    recfn = os.path.abspath(os.path.join(dsetdir, series_name))

    if app.config['ALWAYS_MAKE_PLOTS_AT_SERIES_REQUEST']:
        plotsparam = ''
    else:
        plotsdir = os.path.join(app.root_path, app.config['PLOTS_DIR'])
        plotsparam = ", writeplots=('{}', {})".format(plotsdir, app.config['DEG_F'])

    code = dedent("""
    from envwatcher.bme280 import BME280Recorder
    from envwatcher.file_recorder import output_session_file
    print("Initalizing recorder")
    b = BME280Recorder()
    b.read()
    print("Starting output session")
    output_session_file(b, '{recfn}', {waittime}, progressfn='{progressfn}'{plotsparam})
    print("Finished output session")
    """).format(**locals()).strip()

    subproclogfn = progressfn + '.log'
    with open(subproclogfn, 'a') as logf:
        p = subprocess.Popen([sys.executable, '-c', ';'.join(code.split('\n'))],
                             stdout=logf, stderr=subprocess.STDOUT)
        # make sure the process has time to actually start up but also die if it needs to
        time.sleep(3)
        logf.flush()

    if p.poll() is None:
        return 'Recorder started!'
    else:
        stdouterr = p.communicate()[0]
        return 'Starting recorder failed with: <br><pre>' + stdouterr.decode() + '</pre>'


@app.route("/stop_recorder", methods=['POST'])
def stop_recorder():
    dsetdir = os.path.join(app.root_path, app.config['DATASETS_DIR'])
    stopfn = os.path.join(dsetdir, app.config['PROGRESS_NAME']) + '_stop'
    print('Writing to', stopfn)
    with open(stopfn, 'w') as f:
        f.write('Stop recording!')

    return 'Recorder will be stopped, although it may take roughly the wait time.'
