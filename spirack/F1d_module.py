from .spi_rack import SPI_rack
from .chip_mode import *

class F1d_module(object):
    """F1d module interface class

    This class does the low level interfacing with the F1d IQ-Mixer module.
    It requires an SPI Rack object and module number at initialization.

    Allows the user to read the RF and LO power levels. Next to that a status bit
    can be checked to see if the RF power level clipped. This bit needs to be cleared
    manually after reading. If the remote control is enabled, it also allows the user
    to set the I/Q gain and filter settings remotely. The module then ignores the
    front switch settings until remote control is disabled again.

    Attributes:
        module: the module number set by the user (must coincide with hardware)
        remote_settings: contains a byte with the remote settigns (IQ gain and filter)
    """

    def __init__(self, spi_rack, module):
        """Inits F1d module class

        The F1d module needs an SPI_rack class for communication. Clears the RF clipped
        bit a startup.

        Args:
            spi_rack: SPI_rack class object via which the communication runs
            module: module number set on the hardware
        Example:
            F1d = F1d_module(SPI_Rack_1, 4)
        """
        # Set module number for Chip Select
        self.module = module
        # Give the spi_rack object to use
        self.spi_rack = spi_rack
        # Byte containing Filter, Gain and RF Clip settings
        self.remote_settings = 0x40
        self.clear_rf_clip()

    def read_adc(self, channel):
        """Reads the ADC for RF/LO power

        Reads the given ADC channel. These channels are connected to the outputs
        of RF power detectors. Output needs to be converted to dBm. Function
        used internally.

        Args:
            channel (int: 0-1): the ADC channel to be read
        Returns:
            12-bit ADC data (int)
        """
        s_data = bytearray([1, 160|(channel<<6), 0])
        r_data = self.spi_rack.read_data(self.module, 1, MCP320x_MODE, MCP320x_SPEED, s_data)
        return (r_data[1]&0xF)<<8 | r_data[2]

    def enable_remote(self, enable):
        """Enables remote control of module

        Set to 1/True to enable remote control and 0/False to disable. If enabled,
        switches on the module are ignored and all control happens remotely.

        Args:
            enable (bool/int: 0-1): enables/disables remote control
        """
        self.spi_rack.write_data(self.module, 5, 0, BICPINS_SPEED, bytearray([enable]))

    def clear_rf_clip(self):
        """Clears rf clip bit

        Use this function to clear the RF clip bit once it has been read.
        """
        self.spi_rack.write_data(self.module, 0, 0, BICPINS_SPEED, bytearray([self.remote_settings&0x3F]))
        self.spi_rack.write_data(self.module, 0, 0, BICPINS_SPEED, bytearray([self.remote_settings|0x40]))

    def rf_clipped(self):
        """Return if the RF clipped

        If the RF clipped since the last RF bit reset, returns True. Else returns False.

        Returns:
            True/False depending if the RF clipped (bool)
        """
        data = self.spi_rack.read_data(self.module, 4, 0, BICPINS_SPEED, bytearray([0]))
        return bool(data[0]&0x01)

    def set_IQ_filter(self, value):
        """Sets IQ filter

        Set the IF output filter on both the I and Q channel. In addition to the
        filter values on the front of the module, a fourth higher cutoff frequency
        is possible via software.

        Args:
            value (int): cutoff frequency in MHz. Possible values: 1, 3, 10, 20
        Raises:
            ValueError: if value parameter is not in the list of possible values
        """
        possible_values = [1, 3, 10, 30]
        if value not in possible_values:
            raise ValueError('Value {} does not exist. Possible values are: {}'.format(value, possible_values))

        self.remote_settings &= 0x7C
        if value == 3:
            self.remote_settings |= 3
        elif value == 10:
            self.remote_settings |= 2
        elif value == 30:
            self.remote_settings |= 1

        self.spi_rack.write_data(self.module, 0, 0, BICPINS_SPEED, bytearray([self.remote_settings]))

    def set_I_gain(self, value):
        """Sets I channel gain

        Sets the gain for the I output channel. Values are the same as on the front
        of the module.

        Args:
            value (string): cutoff frequency in MHz. Possible values: 'LOW', 'MID','HIGH'
        Raises:
            ValueError: if value parameter is not in the list of possible values
        """
        possible_values = ['LOW', 'MID', 'HIGH']
        if value.upper() not in possible_values:
            raise ValueError('Value {} does not exist. Possible values are: {}'.format(value, possible_values))

        self.remote_settings &= 0x73
        value = value.upper()
        if value == 'LOW':
            self.remote_settings |= (1<<2)
        elif value == 'MID':
            self.remote_settings |= (3<<2)
        else:
            self.remote_settings |= (2<<2)
        self.spi_rack.write_data(self.module, 0, 0, BICPINS_SPEED, bytearray([self.remote_settings]))

    def set_Q_gain(self, value):
        """Sets Q channel gain

        Sets the gain for the Q output channel. Values are the same as on the front
        of the module.

        Args:
            value (string): cutoff frequency in MHz. Possible values: 'LOW', 'MID','HIGH'
        Raises:
            ValueError: if value parameter is not in the list of possible values
        """
        possible_values = ['LOW', 'MID', 'HIGH']
        if value.upper() not in possible_values:
            raise ValueError('Value {} does not exist. Possible values are: {}'.format(value, possible_values))

        self.remote_settings &= 0x4F
        value = value.upper()
        if value == 'LOW':
            self.remote_settings |= (1<<4)
        elif value == 'MID':
            self.remote_settings |= (3<<4)
        else:
            self.remote_settings |= (2<<4)
        self.spi_rack.write_data(self.module, 0, 0, BICPINS_SPEED, bytearray([self.remote_settings]))

    def get_RF_level(self):
        """Get RF input power

        Calculates the RF input power from the ADC value. Within 4 dB accurate
        upto 4 dBm. Above will deviate more, but that is also above the clipping level.

        Returns:
            power (float): RF input power in dBm
        """
        ADC_data = self.read_adc(0)
        # Fit parameters from measured data and least squares fitting
        a = -39.2088541721
        b = 0.0143584823765
        return a + b*ADC_data

    def get_LO_level(self):
        """ Get LO input power

        Calculates the RF input power from the ADC value. Within 4 dB accurate
        upto 4 dBm. Above will deviate more, but that is also above the clipping level.

        Returns:
            power (float): LO input power in dBm
        """
        ADC_data = self.read_adc(1)
        # Fit parameters from measured data and least squares fitting
        a = -39.2088541721
        b = 0.0143584823765
        return a + b*ADC_data
