import numpy as np


def read_dataset(fn):
    with open(fn) as f:
        firstline = f.readline().strip()
    fields = firstline.split(',')
    dt = np.dtype([(fi, 'S19' if fi=='time' else float) for fi in fields])
    
    return np.loadtxt(fn, dt, skiprows=1, delimiter=',')

def temphum_to_dewpoint(temp, rh):
    """
    Uses the Sonntag90 constants
    """
    a = 6.112 #mbar
    b = 17.62
    c = 234.12 # deg C

    # this is the Magnus fomula
    gamma = np.log(rh/100.) + b*temp/(c + temp)
    return c* gamma/(b - gamma)