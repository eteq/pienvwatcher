import os

from flask import Flask, render_template, abort, send_file

import matplotlib
matplotlib.use('agg')  # non-interactive backend
from .plots import write_series_plots

DATASETS_DIR = 'datasets'
PLOTS_DIR = 'plots'
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
    if os.path.isdir(dsetdir):
        dsls = os.listdir(dsetdir)
        for fn in dsls:
            if fn.endswith('_cal'):
                series.append(fn[:-4])

    return render_template('index.html', series=series)


@app.route("/series/<series_name>")
def series(series_name):
    dsetfn = os.path.join(app.root_path, app.config['DATASETS_DIR'], series_name + '_cal')
    plotsdir = os.path.join(app.root_path, app.config['PLOTS_DIR'])
    plot_names = write_series_plots(dsetfn, plotsdir, app.config['DEG_F'])
    plots = [dict(name=nm, path='/plots/'+path) for nm, path in plot_names]
    return render_template('series.html', series_name=series_name, plots=plots)

@app.route("/plots/<plotid>")
def plots(plotid):
    if plotid.startswith('..') or plotid.startswith('/'):
        abort(404)
    plotfn = os.path.join(app.root_path, app.config['PLOTS_DIR'], plotid)
    return send_file(plotfn)