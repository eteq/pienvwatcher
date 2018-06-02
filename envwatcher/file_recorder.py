import os
import time

from .utils import check_for_recorder

from RPi import GPIO
GPIO.setmode(GPIO.BCM)

# These are for the ACT LED on the RPi 2 B (40 pins)
LED_PATH = '/sys/class/leds/led0/'
LED_GPIO_NUM = 47

def output_session_file(bme280, fn, waitsec=30, writecal=True, writeraw=True,
                                progressfn=None, writeplots=False, setled=True):
    if writeplots:
        import matplotlib
        matplotlib.use('agg')
        from .plots import write_series_plots

    fnraw = fn + '_raw'
    fncal = fn + '_cal'

    if writeraw:
        if not os.path.exists(fnraw):
            with open(fnraw, 'w') as f:
                f.write('time,pressure,temperature,humidity')
                f.write('\n')
    if writecal:
        if not os.path.exists(fncal):
            with open(fncal, 'w') as f:
                f.write('time,pressure,temperature,humidity')
                f.write('\n')

    if progressfn:
        if check_for_recorder(progressfn):
            raise IOError('Progress file for recorder "{}" present.  Cannot'
                          ' start new recorder until it is '
                          'cleared.'.format(progressfn))
        stopfn = progressfn + '_stop'
    else:
        stopfn = ''

    try:
        time.sleep(waitsec)
        oldraw = raw_match = None
        while True:
            if os.path.exists(stopfn):
                break

            sttime = time.time()
            timestr = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(sttime))

            progress_info = {}

            if setled:
                led_on(progress_info)

            raw = bme280.read_raw()
            if raw == oldraw:
                # danger sign... if they are *exactly* the same the reader may 
                # have gotten stuck.  If it happens again, reset
                if raw_match:
                    # guess we've got to reset...
                    progress_info['Reset-occurred'] = True
                    bme280.reset_device()
                else:
                    raw_match = True
            else:
                raw_match = False
            oldraw = raw

            if writeraw:
                with open(fnraw, 'a') as f:
                    towrite = [timestr]
                    towrite.extend([str(r) for r in raw])
                    f.write(','.join(towrite))
                    f.write('\n')

            if writecal:
                pres, temp, hum = bme280.read(raw)
                with open(fncal, 'a') as f:
                    f.write(','.join([timestr, str(pres), str(temp), str(hum)]))
                    f.write('\n')

            if writeplots:
                if isinstance(writeplots, str):
                    plotsdir = writeplots
                    degf = False
                else:
                    plotsdir, degf = writeplots
                plot_names = write_series_plots(fncal, plotsdir, degf)
            else:
                plot_names = None

            proc_time = time.time() - sttime
            progress_info.update({
                            'Expires-on': str(time.time() + (proc_time + waitsec)*2),
                            'PID': str(os.getpid()),
                            'Output(s)': [],
                            'Sample-time(s)': str(waitsec),
                            'Series name': os.path.split(fn)[1]
                            })
            if writecal:
                progress_info['Output(s)'].append(fncal)
            if writeraw:
                progress_info['Output(s)'].append(fnraw)
            if len(progress_info['Output(s)']) == 0:
                del progress_info['Output(s)']

            if plot_names is not None:
                progress_info['Plot names'] = plotnames = []
                for i, (name, path) in enumerate(plot_names):
                    plotnames.append(name + '|' + path)

            if progressfn:
                with open(progressfn, 'w') as fw:
                    for nm, val in progress_info.items():
                        fw.write(nm)
                        fw.write(': ')
                        if isinstance(val, str):
                            fw.write(val)
                        else:
                            #assume an iterable
                            fw.write(', '.join(val))
                        fw.write('\n')

            if setled:
                led_off(progress_info)

            timeleft = sttime - time.time() + waitsec
            if timeleft > 0:
                time.sleep(timeleft)
    finally:
        # remove the stop and progress files
        if os.path.exists(stopfn):
            os.unlink(stopfn)
        if os.path.exists(progressfn):
            os.unlink(progressfn)


def led_on(progress_info={}):
    with open(LED_PATH + 'trigger', 'r') as f:
        triggerinfo = f.read()
    if '[oneshot]' in triggerinfo:
        try:
            progress_info['LED setting'] = 'oneshot'
            with open(LED_PATH + 'shot', 'w') as f:
                f.write('shot')
        except PermissionError:
            progress_info['LED setting'] = ('Failed due to inacessible oneshot.'
                                            ' Need to do "sudo chmod o+w '
                                            '{}shot"').format(LED_PATH)
    elif '[gpio]' in triggerinfo:
        GPIO.setup(LED_GPIO_NUM, GPIO.OUT)
        GPIO.output(LED_GPIO_NUM, 1)
        progress_info['LED setting'] = 'GPIO on Pin {}'.format(LED_GPIO_NUM)
    else:
        # do nothing because we can't do anything
        progress_info['LED setting'] = ('No LED setting option available.  You '
                                        'probably want to send either "gpio" or'
                                        ' "oneshot" to {}trigger').format(LED_PATH)


def led_off(progress_info={}):
    with open(LED_PATH + 'trigger', 'r') as f:
        triggerinfo = f.read()
    if '[gpio]' in triggerinfo:
        GPIO.output(LED_GPIO_NUM, 0)
    # otherwise do nothing because we can't do anything
