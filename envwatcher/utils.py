import os
import time

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


def deg_f_to_c(degf):
    return (degf - 32) / 1.8


def deg_c_to_f(degc):
    return degc*1.8 + 32
    

def check_for_recorder(recorder_fn, infodct=None):
    # Should probably do some locking here just in case?  Or maybe it's atomic-enough?
    if infodct is None:
        infodct = {}
    if os.path.isfile(recorder_fn):
        with open(recorder_fn, 'r') as f:
            rec = f.read()

        for l in rec.split('\n'):
            res = l.strip().split(':')
            if len(res) == 1:
                continue
            elif len(res) == 2:
                infodct[res[0]] = res[1].strip()
            else:
                raise ValueError('Invalid line encountered in recorder file '
                                 '"{}"!: "{}"'.format(recorder_fn, l))

        if 'Expires-on' in infodct:
            expire_time = float(infodct['Expires-on'])
            if expire_time > time.time():
                return True
        else:
            raise ValueError('Expires-on entry not found in recorder file '
                             '"{}"'.format(recorder_fn))
    return False
