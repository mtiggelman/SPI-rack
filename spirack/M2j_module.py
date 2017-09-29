from .spi_rack import SPI_rack
from .chip_mode import *

class M2j_module(object):

    def __init__(self, spi_rack, module):
        # Set module number for Chip Select
        self.module = module
        # Give the spi_rack object to use
        self.spi_rack = spi_rack

        # Set DAC reference to 2.5V internal
        s_data = bytearray([0b01110001,0,0])
        self.spi_rack.write_data(self.module, 0, MAX5702_MODE, MAX5702_SPEED, s_data)

    def get_level(self):
        s_data = bytearray([0, 0])
        r_data = self.spi_rack.read_data(self.module, 1, MCP320x_MODE, MAX5702_SPEED, s_data)
        return (r_data[0]&0x0F)<<8 | r_data[1]

    def set_gain(self, level):
        s_data = bytearray([0b10000010, (level&0xFF0)>>4, (level&0x0F)<<4])
        self.spi_rack.write_data(self.module, 0, MAX5702_MODE, MAX5702_SPEED, s_data)

    def clear_rf_clip(self):
        # SPI address 5 for writing
        # Resets clipped bit
        self.spi_rack.write_data(self.module, 5, 0, 6, bytearray([0xF7]))
        self.spi_rack.write_data(self.module, 5, 0, 6, bytearray([0xFF]))

    def rf_clipped(self):
        # SPI adress 6 for reading
        # Return True if clipped, False if not clipped
        inputs = spi_rack.read_data(2, 6, 0, bytearray([0x00]))
        inputs = int.from_bytes(inputs, byteorder='big')
        inputs = (inputs>>3)&0x01
        return bool(inputs)
