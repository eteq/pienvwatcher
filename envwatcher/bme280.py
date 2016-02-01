import os
import time

import numpy as np
import smbus



# register addresses
ID_REGISTER = 0xD0
STATUS_REGISTER = 0xF3
RESET_REGISTER = 0xE0
CTRL_HUM_REGISTER = 0xF2
CTRL_MEAS_REGISTER = 0xF4
CONFIG_REGISTER = 0xF5
DATA_START = 0xF7

BME280_ID = 0x60
RESET_CODE = 0xB6

CALIB_REGISTERS = { 'dig_T1': ('ushort', 0x88, 0x89),
                    'dig_T2': ('short', 0x8a, 0x8b),
                    'dig_T3': ('short', 0x8c, 0x8d),
                    'dig_P1': ('ushort', 0x8e, 0x8f),
                    'dig_P2': ('short', 0x90, 0x91),
                    'dig_P3': ('short', 0x92, 0x93),
                    'dig_P4': ('short', 0x94, 0x95),
                    'dig_P5': ('short', 0x96, 0x97),
                    'dig_P6': ('short', 0x98, 0x99),
                    'dig_P7': ('short', 0x9a, 0x9b),
                    'dig_P8': ('short', 0x9c, 0x9d),
                    'dig_P9': ('short', 0x9e, 0x9f),
                    'dig_H1': ('uint8', 0xa1),
                    'dig_H2': ('short', 0xe1, 0xe2),
                    'dig_H3': ('uint8', 0xe3),
                    'dig_H4': ('12ml', 0xe4, 0xe5),
                    'dig_H5': ('12lm', 0xe5, 0xe6),
                    'dig_H6': ('int8', 0xe7),
                    }

class BME280Recorder:
    def __init__(self, address=0x77, i2cbusnum=1, mode='forced'):
        self.i2cbusnum = i2cbusnum
        self.bus = smbus.SMBus(self.i2cbusnum)
        self.address = address

        self.check_device_present()

        self.reset_device()
        # initial mode is sleep after reset
        self._mode = 'sleep'

        self.humidity_oversampling = 8
        self.pressure_oversampling = 16
        self.temperature_oversampling = 2

        self.t_standby_ms = 250
        self.iir_filter = 0

        self.mode = mode

        self.calib_vals = self.get_calibs()
    
    def check_device_present(self):
        devid = self.read_register(ID_REGISTER)
        if devid != BME280_ID:
            raise ValueError('Device is not a BME280 (id != 60).')

    def reset_device(self):
        self.bus.write_byte_data(self.address, RESET_REGISTER, RESET_CODE)
        time.sleep(0.5)  # make sure it finishes resetting
        self.check_device_present()

    def get_calibs(self):
        calib_vals = {}
        for nm, typeandregs in CALIB_REGISTERS.items():
            dt = typeandregs[0]
            regs = typeandregs[1:]

            regvals = []
            for i, reg in enumerate(regs):
                    regvals.append(self.read_register(reg))

            if dt == '12ml':
                regval = regvals[0] << 4  # 11:4
                regval += regvals[1] & 0b111  # 3:0 -> 3:0
                calib_vals[nm] = np.array(regval, dtype='short')
            elif dt == '12lm':
                regval = regvals[0] & 0b11110000  # 7:4 -> 3:0
                regval += regvals[1]  # 11:4
                calib_vals[nm] = np.array(regval, dtype='short')
            else:
                regvals = [val << (8*i) for i, val in enumerate(regvals)]
                calib_vals[nm] = np.sum(regvals, dtype=dt)
        return calib_vals

    def read_register(self, regaddr):
        return self.bus.read_byte_data(self.address, regaddr)

    def set_register(self, regaddr, val, startbit=0, nbits=8):
        if (len(bin(val))-2) > nbits:
            raise ValueError('input value has too many bits')
        if (nbits + startbit) > 8:
            raise ValueError('Trying to set more than 8 bits in the register')

        if nbits == 8:
            new_regval = val
        else:
            regval = self.read_register(regaddr)
            # first clear out the old value
            new_regval = regval & ~((2**nbits-1) << startbit)
            # now apply the new one
            new_regval |= val << startbit

        self.bus.write_byte_data(self.address, regaddr, new_regval)

    def _read_raw(self):
        """
        Reads the pressure, temperature, and humidity from their registers and 
        returns them as raw ADC integers.

        Note that this does *not* force a read in forced mode - use `read` for
        that.
        """
        data_regs = self.bus.read_i2c_block_data(0x77, DATA_START, 8)

        pres_val = data_regs[2] >> 4
        pres_val +=  data_regs[1] << 4
        pres_val +=  data_regs[0] << 12

        temp_val = data_regs[5] >> 4
        temp_val +=  data_regs[4] << 4
        temp_val +=  data_regs[3] << 12

        hum_val = data_regs[7] + (data_regs[6] << 8) 

        return pres_val, temp_val, hum_val

    def read(self, raw=True):
        """
        Reads the current pressure, temperature, humidity values and returns
        them.  If `raw` is True, it is the raw ADC value, otherwise it's the
        calibrated value.
        """
        if self._mode == 'forced':
            self.set_register(CTRL_MEAS_REGISTER, 0b01, 0, 2)
            # wait for a ms, which should be plenty of time
            time.sleep(0.001)

        pres_raw, temp_raw, hum_raw = self._read_raw()
        if raw:
            return pres_raw, temp_raw, hum_raw
        else:
            t_fine_in = -self._raw_to_t_fine(temp_raw)
            temp = self.raw_to_calibrated_temp(t_fine_in)
            pres = self.raw_to_calibrated_pressure(pres_raw, t_fine_in)
            hum = self.raw_to_calibrated_humidity(hum_raw, t_fine_in)
            return pres, temp, hum

    def _raw_to_t_fine(self, rawtemp):
        """
        Used in all the other calibration formulae
        """
        if rawtemp < 0:
            return -rawtemp
        else:
            T_adc = np.array(rawtemp, dtype='int32')
            dig_T1 = self.calib_vals['dig_T1'].astype('int32')
            dig_T2 = self.calib_vals['dig_T2'].astype('int32')
            dig_T3 = self.calib_vals['dig_T3'].astype('int32')

            # from the BME280 datasheet
            var1 = (((T_adc>>3) - (dig_T1<<1)) * dig_T2) >> 11
            var2 = (((((T_adc>>4) - dig_T1) * ((T_adc>>4) - dig_T1)) >> 12) * dig_T3) >> 14
            return var1 + var2


    def raw_to_calibrated_temp(self, rawtemp):
        """
        If rawtemp is negative, it's interpreted as -t_fine
        """
        t_fine = self._raw_to_t_fine(rawtemp)
        deg_C = ((t_fine * 5 + 128) >> 8)/100.
        return deg_C

    def raw_to_calibrated_pressure(self, rawpressure, rawtemp):
        """
        If rawtemp is negative, it's interpreted as -t_fine

        Returns pressure in kPa
        """
        t_fine = self._raw_to_t_fine(rawtemp)

        adc_P = np.array(rawpressure, dtype='int64')
        dig_P1 = self.calib_vals['dig_P1'].astype('int64')
        dig_P2 = self.calib_vals['dig_P2'].astype('int64')
        dig_P3 = self.calib_vals['dig_P3'].astype('int64')
        dig_P4 = self.calib_vals['dig_P4'].astype('int64')
        dig_P5 = self.calib_vals['dig_P5'].astype('int64')
        dig_P6 = self.calib_vals['dig_P6'].astype('int64')
        dig_P7 = self.calib_vals['dig_P7'].astype('int64')
        dig_P8 = self.calib_vals['dig_P8'].astype('int64')
        dig_P9 = self.calib_vals['dig_P9'].astype('int64')

        var1 = t_fine - 128000
        var2 = var1 * var1 * dig_P6
        var2 += ((var1*dig_P5)<<17)
        var2 += ((dig_P4)<<35)
        var1 = ((var1 * var1 * dig_P3)>>8) + ((var1 * dig_P2)<<12)
        var1 = ((((1)<<47)+var1))*(dig_P1)>>33

        p = 1048576-adc_P
        p = (((p<<31)-var2)*3125)//var1
        var1 = (dig_P9 * (p>>13) * (p>>13)) >> 25
        var2 = (dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (dig_P7<<4)
        return p/256000.

    def raw_to_calibrated_humidity(self, rawhumidity, rawtemp):
        """
        If rawtemp is negative, it's interpreted as -t_fine
        """
        t_fine = self._raw_to_t_fine(rawtemp)

        adc_H = np.array(rawhumidity, dtype='int32')
        dig_H1 = self.calib_vals['dig_H1'].astype('int32')
        dig_H2 = self.calib_vals['dig_H2'].astype('int32')
        dig_H3 = self.calib_vals['dig_H3'].astype('int32')
        dig_H4 = self.calib_vals['dig_H4'].astype('int32')
        dig_H5 = self.calib_vals['dig_H5'].astype('int32')
        dig_H6 = self.calib_vals['dig_H6'].astype('int32')
        
        var = t_fine - 76800
        var = ((((adc_H << 14) - (dig_H4 << 20) - (dig_H5 * var)) + 16384) >> 15) * (((((((var * dig_H6) >> 10) * (((var *(dig_H3) >> 11) + 32768)) >> 10) + 2097152) * (dig_H2) + 8192) >> 14))
        var -= (((((var >> 15) * (var >> 15)) >> 7) * dig_H1) >> 4)
        var.ravel()[var.ravel()<0] = 0
        var.ravel()[var.ravel()>419430400] = 419430400
        return (var>>12)/1024.

    @property
    def mode(self):
        return self._mode
    @mode.setter
    def mode(self, val):
        if val == 'sleep' or val == 'forced':
            self.set_register(CTRL_MEAS_REGISTER, 0b0, 0, 2)
        elif val == 'normal':
            self.set_register(CTRL_MEAS_REGISTER, 0b11, 0, 2)
        else:
            raise ValueError('Invalid mode {}'.format(val))
        self._mode = val

    @property
    def t_standby_ms(self):
        return self._t_standby_ms
    @t_standby_ms.setter
    def t_standby_ms(self, val):
        if val == 0.5:
            regval = 0b000
        elif val == 62.5:
            regval = 0b001
        elif val == 125:
            regval = 0b010
        elif val == 250:
            regval = 0b011
        elif val == 500:
            regval = 0b100
        elif val == 1000:
            regval = 0b101
        elif val == 10:
            regval = 0b110
        elif val == 20:
            regval = 0b111
        else:
            raise ValueError('Invalid t_standby_ms: {}'.format(val))

        self.set_register(CONFIG_REGISTER, regval, 5, 3)

        self._t_standby_ms = val


    def _oversampling_val_to_regval(self, val):
        if val == 0:
            return 0
        elif val == 1:
            return 0b001
        elif val == 2:
            return 0b010
        elif val == 4:
            return 0b011
        elif val == 8:
            return 0b100
        elif val == 16:
            return 0b101
        else:
            raise ValueError('Invalid oversampling value {}'.format(val))

    @property
    def humidity_oversampling(self):
        return self._humidity_oversampling
    @humidity_oversampling.setter
    def humidity_oversampling(self, val):
        if val is None:
            val = 0

        if getattr(self, '_humidity_oversampling', None) == val:
            return

        regval = self._oversampling_val_to_regval(val)
        self.set_register(CTRL_HUM_REGISTER, regval, 0, 3)

        # Datasheet 5.4.5 says you need to write to the ctrl_meas to get the 
        # humidity settings to change
        measval = self.read_register(CTRL_MEAS_REGISTER)
        self.set_register(CTRL_MEAS_REGISTER, measval)

        self._humidity_oversampling = val

    @property
    def pressure_oversampling(self):
        return self._pressure_oversampling
    @pressure_oversampling.setter
    def pressure_oversampling(self, val):
        if val is None:
            val = 0

        if getattr(self, '_pressure_oversampling', None) == val:
            return

        regval = self._oversampling_val_to_regval(val)
        self.set_register(CTRL_MEAS_REGISTER, regval, 2, 3)

        self._pressure_oversampling = val

    @property
    def temperature_oversampling(self):
        return self._temperature_oversampling
    @temperature_oversampling.setter
    def temperature_oversampling(self, val):
        if val is None:
            val = 0

        if getattr(self, '_temperature_oversampling', None) == val:
            return

        regval = self._oversampling_val_to_regval(val)
        self.set_register(CTRL_MEAS_REGISTER, regval, 5, 3)

        self._temperature_oversampling = val

    @property
    def iir_filter(self):
        return self._iir_filter
    @iir_filter.setter
    def iir_filter(self, val):
        if val is None:
            val = 0

        if getattr(self, '_iir_filter', None) == val:
            return

        if val == 0:
            regval = 0
        elif val == 2:
            regval = 0b001
        elif val == 4:
            regval = 0b010
        elif val == 8:
            regval = 0b011
        elif val == 16:
            regval = 0b100
        else:
            raise ValueError('Requested IIR filter value {} invalid'.format(val))

        self.set_register(CONFIG_REGISTER, regval, 0, 3)
        self._iir_filter = val

    def output_session_file(self, fn, waitsec=30, writecal=True, writeraw=True):

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

        while True:
            sttime = time.time()
            timestr = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime(sttime))

            pres_raw, temp_raw, hum_raw = self.read()

            if writeraw:
                with open(fnraw, 'a') as f:
                    f.write(','.join([timestr, str(pres_raw), str(temp_raw), str(hum_raw)]) + '\n')

            if writecal:
                t_fine_in = -self._raw_to_t_fine(temp_raw)
                temp = self.raw_to_calibrated_temp(t_fine_in)
                pres = self.raw_to_calibrated_pressure(pres_raw, t_fine_in)
                hum = self.raw_to_calibrated_humidity(hum_raw, t_fine_in)
                with open(fncal, 'a') as f:
                    f.write(','.join([timestr, str(pres), str(temp), str(hum)]) + '\n')


            timeleft = sttime - time.time() + 30
            if timeleft > 0:
                time.sleep(timeleft)
