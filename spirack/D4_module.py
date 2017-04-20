from .spi_rack import *
from .D4_constants import *
from .chip_mode import *

import time

class D4_module(object):
    def __init__(self, spi_rack, module):
        # Set module and chip number for Chip Select
        self.module = module
        # Give the spi_rack object to use
        self.spi_rack = spi_rack
        self.mode = 0
        self.filter_val = 16
        self.buf_en = 1
        # Setup the ADC with standard values
        self.setup_ADC()

    def setup_ADC(self):
        # For both ADC chips (ADC=0 and ADC=1)
        for ADC in range(0,2):
            # Disable internal reference and single conversion
            # Extra: single cycle
            self.write_data(ADC, MODE_REG, 0<<REF_EN | self.mode<<MODE | 1<<SING_CYC)
            #
            self.write_data(ADC, IFMODE, 1<<DOUT_RESET)
            # Set config reg 0 to binary coded offset
        	# Set input buffers enabled, reference buffers disabled, external reference
            self.write_data(ADC, CONFIG_REG, (1<<BI_UNIPOLAR) | (0b00<<REF_SEL) | (self.buf_en<<AINBUF0P) | (self.buf_en<<AINBUF0M) )
            # Set CH1, Enable, setup0, meas diff between AIN2 and AIN3
            self.write_data(ADC, CH1_REG, (1<<CH_EN) | (0b000<<SETUP_SEL) | (AIN0<<AINPOS) | (AIN4<<AINNEG))
            # Set CH2/3/4, Disable, setup0, AINx - AIN4
            self.write_data(ADC, CH2_REG, (0<<CH_EN) | (0b000<<SETUP_SEL) | (AIN1<<AINPOS) | (AIN4<<AINNEG))
            self.write_data(ADC, CH3_REG, (0<<CH_EN) | (0b000<<SETUP_SEL) | (AIN2<<AINPOS) | (AIN4<<AINNEG))
            self.write_data(ADC, CH4_REG, (0<<CH_EN) | (0b000<<SETUP_SEL) | (AIN3<<AINPOS) | (AIN4<<AINNEG))
            # Filter: sinc3 at 50Hz output rate, 12.8 Hz -3dB point: 60 ms settling
            self.write_data(ADC, FILTER_REG, (0b11<<ORDER0) | (self.filter_val<<ODR))

    def write_data(self, ADC, reg, data):
        """
        Write given data to register of the given ADC
        """
        s_data = bytearray([reg, data>>8, data & 0xFF])
        self.spi_rack.write_data(self.module, ADC, AD7175_MODE, s_data)

    def read_data(self, ADC, reg, no_bytes):
        """
        Read a given number of bytes (no_bytes) from given ADC register
        """

        s_data = bytearray([ reg | (1<<6)] + no_bytes*[0])
        r_i_data = self.spi_rack.read_data(self.module, ADC, AD7175_MODE, s_data)

        return r_i_data

    def singleConversion(self, ADC):
        """
        Start one conversion and keep waiting until conversion is done
        Give back calculated voltage
        """
        if self.mode == 1:
            self.write_data(ADC, MODE_REG, 0<<REF_EN | 1<<MODE | 1<<SING_CYC)
        else:
            self.write_data(ADC, FILTER_REG, (0b11<<ORDER0) | (self.filter_val<<ODR))
        while(True):
            #time.sleep(0.05)
            status = self.read_data(ADC, STATUS_REG, 1)
            #print("Status: " + str(status[0]))

            # if new data available:
            if (status[0]&(1<<7)) == 0:
                # Get raw data, shift to correct place and convert to voltage
                raw_data = self.read_data(ADC, DATA_REG, 3)
                raw_data = raw_data[1:]
                raw_data_val = raw_data[0] << 16 | raw_data[1] << 8 | raw_data[2]
                #print("Raw data: " + str(bin(raw_data_val)))
                # For differential, use 10 Volt instead of 5 Volt
                return (5.0/(2**24)*raw_data_val) - 2.5;
                #return (10.0/(2**24)*raw_data_val) - 5;
