import os
from datetime import datetime

import numpy as np
from matplotlib import pyplot as plt


def read_dataset(fn):
    with open(fn) as f:
        firstline = f.readline().strip()
    fields = firstline.split(',')
    dt = np.dtype([(fi, 'S19' if fi=='time' else float) for fi in fields])
    
    return np.loadtxt(fn, dt, skiprows=1, delimiter=',')


def write_series_plots(dsetfn, outdir):
    from matplotlib.dates import date2num

    dset_name = os.path.split(dsetfn)[-1]

    if dset_name.endswith('_cal'):
        dset_name = dset_name[:-4]
    else:
        raise ValueError('dsets have to end in _cal')

    dset = read_dataset(dsetfn)
    dts = [datetime.strptime(t.decode(), '%Y-%m-%d_%H:%M:%S') for t in dset['time']]
    plotdates = date2num(dts)

    plot_names = []
    for name in dset.dtype.names[1:]:
        plt.figure()

        plt.plot_date(plotdates, dset[name], '-')

        plt.xlabel('Date')
        plt.ylabel(name)

        img_name = '{}_{}.png'.format(dset_name, name)
        plt.savefig(os.path.join(outdir, img_name))
        plt.close()
        
        plot_names.append((name, img_name))

    return plot_names

def triple_plots(fntab):
    from astropy.table import Table
    from astropy.time import Time

    if isinstance(fntab, str):
        tab = Table.read(fntab, format='csv')

    ts = Time([time.mktime(time.strptime(ti,'%Y-%m-%d_%H:%M:%S')) - 5*3600. for ti in tab['time']],format='unix').plot_date

    ax1 = plt.subplot(3, 1, 1)
    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)

    ax1.plot_date(ts, tab['temperature'],'-')
    ax1.set_ylabel('Temperature')
    ax2.plot_date(ts, tab['pressure'],'-')
    ax2.set_ylabel('Pressure')
    ax3.plot_date(ts, tab['humidity'],'-')
    ax3.set_ylabel('Humidity')

    plt.tight_layout()
    plt.subplots_adjust(hspace=0)
