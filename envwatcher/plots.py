import os
from datetime import datetime

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.dates import date2num, num2date, DateFormatter

from .utils import read_dataset, temphum_to_dewpoint


def write_series_plots(dsetfn, outdir):

    dset_name = os.path.split(dsetfn)[-1]

    if dset_name.endswith('_cal'):
        dset_name = dset_name[:-4]
    else:
        raise ValueError('dsets have to end in _cal')

    dset = read_dataset(dsetfn)
    dts = [datetime.strptime(t.decode(), '%Y-%m-%d_%H:%M:%S') for i, t in enumerate(dset['time'])]
    plotdates = date2num(dts)

    firstdatestr = num2date(plotdates[0]).strftime('%Y-%m-%d')
    lastdatestr = num2date(plotdates[-1]).strftime('%Y-%m-%d')
    if firstdatestr == lastdatestr:
        titlestr = firstdatestr
    else:
        titlestr = firstdatestr + ' to ' + lastdatestr

    data_to_plot = {nm: dset[nm] for nm in dset.dtype.names[1:]}

    if 'dewpoint' not in data_to_plot and ('temperature' in data_to_plot and 
                                           'humidity' in data_to_plot):
        data_to_plot['dewpoint'] = temphum_to_dewpoint(data_to_plot['temperature'], data_to_plot['humidity'])

    plot_names = []
    for name, data in data_to_plot.items():
        plt.figure()

        plt.plot_date(plotdates, data, '-')

        plt.xlabel('Date')
        if name == 'pressure':
            plt.ylabel('kPa')
        elif name == 'temperature' or name == 'dewpoint':
            plt.ylabel('deg C')
        elif name == 'humidity':
            plt.ylabel('RH %')
        else:
            plt.ylabel(name)

        plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.gcf().autofmt_xdate()
        plt.title(titlestr)

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
