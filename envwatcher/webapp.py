import os
import time
import multiprocessing

from flask import Flask, render_template, abort, send_file


import matplotlib
matplotlib.use('agg')  # non-interactive backend
from .plots import write_series_plots

from .utils import check_for_recorder

DATASETS_DIR = 'datasets'
PLOTS_DIR = 'plots'
PROGRESS_NAME = ''recorder_progress
DEG_F = False

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

    recorder_present = check_for_recorder(recorder_fn)

    if os.path.isdir(dsetdir):
        dsls = os.listdir(dsetdir)
        for fn in dsls:
            if fn.endswith('_cal'):
                series.append(fn[:-4])

    return render_template('index.html', series=series, recorder_present=recorder_present)


@app.route("/series/<series_name>")
def series(series_name):
    dsetfn = os.path.join(app.root_path, app.config['DATASETS_DIR'], series_name + '_cal')
    plotsdir = os.path.join(app.root_path, app.config['PLOTS_DIR'])
    plot_names = write_series_plots(dsetfn, plotsdir, app.config['DEG_F'])
    plots = [dict(name=nm, path='/plots/{}?{}'.format(path,time.time())) 
             for nm, path in plot_names]
    return render_template('series.html', series_name=series_name, plots=plots)


@app.route("/plots/<plotid>")
def plots(plotid):
    if plotid.startswith('..') or plotid.startswith('/'):
        abort(404)
    plotfn = os.path.join(app.root_path, app.config['PLOTS_DIR'], plotid)
    return send_file(plotfn)


@app.route("/recorder", methods=['POST'])
def start_recorder():
    progressfn = os.path.join(dsetdir, app.config['PROGRESS_NAME'])
    if check_for_recorder(progressfn):
        raise IOError('Progress file for recorder "{}" present.  Cannot start '
                      'new recorder until it is cleared.'.format(progressfn))

    series_name = request.form['series']
    waittime = int(request.form['sampletime'])

    recfn = os.path.abspath(os.path.join(dsetdir, series_name))

    ctx = multiprocessing.get_context('spawn')
    p = ctx.Process(target=spawn_recorder, args=(recfn, waittime, progressfn))
    p.start()

    time.sleep(1)  # make sure the process has time to actually start up
    return 'Recorder started!'

def spawn_recorder(recfn, waittime, progressfn):
    from .bme280 import BME280Recorder

    b = BME280Recorder()
    b.output_session_file(recfn, waittime, progressfn=progressfn)


@app.route("/recorder", methods=['DELETE'])
def stop_recorder():
    stopfn = os.path.join(dsetdir, app.config['PROGRESS_NAME'])
    with open(stopfn, 'w') as f:
        f.write('Stop recording!')

    return 'Recorder will be stopped, although it may take roughly the wait time.'