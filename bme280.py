import time

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

class BME280Recorder:
    def __init__(self, address=0x77, i2cbusnum=1):
        self.i2cbusnum = i2cbusnum
        self.bus = smbus.SMBus(self.i2cbusnum)
        self.address = address

        self.check_device_present()

        self.reset_device()
        # initial mode is sleep after reset
        self._mode = 'sleep'

        self.humidity_oversampling = 1
        self.pressure_oversampling = 1
        self.temperature_oversampling = 1

        self.t_standby_ms = 250
        self.iir_filter = 0

        self.mode = 'normal'
    
    def check_device_present(self):
        devid = self.bus.read_byte_data(self.address, ID_REGISTER)
        if devid != BME280_ID:
            raise ValueError('Device is not a BME280 (id != 60).')

    def reset_device(self):
        self.bus.write_byte_data(self.address, RESET_REGISTER, RESET_CODE)
        time.sleep(0.5)  # make sure it finishes resetting
        self.check_device_present()

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

        self.bus.write_byte_data(self.address, regaddr, val)

    def read_raw(self):
        """
        Reads the pressure, temperature, and humidity from their registers and 
        returns them as raw ADC integers.
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
        self._t_standby_ms = val
        raise NotImplementedError


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

        if val == self._humidity_oversampling:
            return

        regval = self._oversampling_val_to_regval(val)
        self.set_register(CTRL_HUM_REGISTER, regval, 0, 3)

        # Datasheet 5.4.5 says you need to write to the ctrl_meas to get the 
        # humidity settings to change
        measval = self.get_register(CTRL_MEAS_REGISTER)
        self.set_register(CTRL_MEAS_REGISTER, measval)

        self._humidity_oversampling = val

    @property
    def pressure_oversampling(self):
        return self._pressure_oversampling
    @pressure_oversampling.setter
    def pressure_oversampling(self, val):
        if val is None:
            val = 0

        if val == self._pressure_oversampling:
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

        if val == self._pressure_oversampling_temperature_oversampling:
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

        if val == self._iir_filter:
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
