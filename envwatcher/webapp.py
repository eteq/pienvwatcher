import os

from flask import Flask, render_template, error, send_file

import matplotlib
matplotlib.use('agg')  # non-interactive backend
from .plots import make_series_plots

DATASETS_DIR = 'datasets'
PLOTS_DIR = 'plots'

app = Flask(__name__.split('.')[0])
app.config.from_object(__name__)


@app.route("/")
@app.route("/index")
def index():
    series = []
    if os.path.isdir(app.config['DATASETS_DIR']):
        dsls = os.listdir(app.config['DATASETS_DIR'])
        for fn in dsls:
            if fn.endswith('_cal'):
                series.append(fn[:-4])

    return render_template('index.html', series=series)


@app.route("/series/<series_name>")
def series(series_name):
    dsetfn = os.path.join(app.config['DATASETS_DIR'], series_name + '_cal')
    plot_names = write_series_plots(dsetfn, app.config['PLOTS_DIR'])
    plots = [dict(name=nm, path=series_name+'_'+path) for nm, path in plot_names]
    return render_template('series.html', series_name=series_name, plots=plots)

@app.route("/plots/<plotid>"):
def plots(plotid):
    if plotid.startswith('..') or plotid.startswith('/'):
        error(404)
    plotfn = os.path.join(app.config['PLOTS_DIR'], plotid + '_cal')
    return send_file(plotfn)