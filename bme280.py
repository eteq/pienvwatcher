import time

import smbus


class BME280Recorder:
    def __init__(self, address=0x77, i2cbusnum=1):
        self.i2cbusnum = i2cbusnum
        self.bus = smbus.SMBus(self.i2cbusnum)
        self.address = address

        self.check_device_present()

        self.reset_device()
    
    def check_device_present(self):
        devid = self.bus.read_byte_data(self.address, 0xD0)
        if devid != hex(0x60):
            raise ValueError('Device is not a BME280 (id != 60).')

    def reset_device(self):
        self.bus.write_byte_data(self.address,0xE0 ,0xB6)
        time.sleep(0.5)  # make sure it finishes resetting
        self.check_device_present()