from .spi_rack import SPI_rack
from .chip_mode import MAX5702_MODE, MAX5702_SPEED, MCP320x_MODE, BICPINS_SPEED

class M2j_module(object):
    """M2j module interface class

    This class does the low level interfacing with the M2j amplifier module. It
    requires a SPI Rack object and module number at initializationself.

    Allows the user to get the RF level before the last amplifier and see if
    the amplifiers are clipping. The user can also set the amplification of the
    module by changing a variable attenuator inside the unit.

    Attributes:
        module: the module number set by the user (must coincide with hardware)
        remote: true if remote control is enabled
    """

    def __init__(self, spi_rack, module, remote=False):
        """Inits M2j module class

        The M2j module needs an SPI_rack class for communication. Resets the dual
        DAC output at startup.

        Args:
            spi_rack: SPI_rack class object via which the communication runs
            module: module number set on the hardware
            remote: enable/disable remote control
        Example:
            M2j = M2j_module(SPI_Rack_1, 5)
        """
        # Set module number for Chip Select
        self.module = module
        # Give the spi_rack object to use
        self.spi_rack = spi_rack

        # Set remote control
        self.enable_remote(remote)

        # Set BIC outputs SPI6 MOSI connected to -CLR Dual DAC      # HvdD
        self.spi_rack.write_data(self.module, 5, 0, 6, bytearray([0xFF]))

        # Set DAC reference to 2.5V internal
        s_data = bytearray([0b01110001, 0, 0])
        self.spi_rack.write_data(self.module, 0, MAX5702_MODE, MAX5702_SPEED, s_data)

    def get_level(self):
        s_data = bytearray([0, 0])
        r_data = self.spi_rack.read_data(self.module, 1, MCP320x_MODE, MAX5702_SPEED, s_data)
        return (r_data[0]&0x0F)<<8 | r_data[1]

    def set_gain(self, level):
        s_data = bytearray([0b10000010, (level&0xFF0)>>4, (level&0x0F)<<4])
        self.spi_rack.write_data(self.module, 0, MAX5702_MODE, MAX5702_SPEED, s_data)

    def enable_remote(self, enable):
        """Enables remote control of module

        Set to 1/True to enable remote control and 0/False to disable. If enabled
        the setting on the front of the module is ignored and all control happens
        remotely.

        Args:
            enable (bool/int: 0-1): enables/disables remote control
        """
        self.remote = enable
        #Keep the clear rf clip high (active low)
        self.spi_rack.write_data(self.module, 5, 0, BICPINS_SPEED, bytearray([self.remote<<5 | 16]))

    def clear_rf_clip(self):
        """Clears rf clip bit

        Resets the rf clip bit.
        """
        # SPI address 5 for writing
        # Resets clipped bit
        self.spi_rack.write_data(self.module, 5, 0, BICPINS_SPEED, bytearray([self.remote<<4]))
        self.spi_rack.write_data(self.module, 5, 0, BICPINS_SPEED, bytearray([self.remote<<4 | 8]))

    def rf_clipped(self):
        """Return if the RF clipped

        If the RF clipped since the last RF bit reset, returns True. Else returns False.

        Returns:
            True/False depending if the RF clipped (bool)
        """

        data = self.spi_rack.read_data(self.module, 6, 0, BICPINS_SPEED, bytearray([0]))
        return bool(data[0]&0x08)
