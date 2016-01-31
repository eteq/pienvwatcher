from matplotlib import pyplot as plt


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
