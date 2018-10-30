"""ADC module D4 interface

SPI Rack interface code for the D4 module.

Example:
    Example use: ::
        D4 = spirack.D4_modules(SPI_Rack1, 5)
"""

from .chip_mode import AD7175_MODE, AD7175_SPEED

class D4_module(object):
    """D4 module interface class

    This class does the low level interfacing with the D4 module. When creating
    an instance, it requires a SPI_rack class passed as a parameter.

    The module contains two independent 24-bit analog to digital converters. They
    can be individually configured and triggered. The filter settings determine
    the data rate and resolution. For an overview of settings, see the website.

    Attributes:
        module (int): module number set by the user (must coincide with hardware)
        filter_setting (int): current filter setting
        filter_type (string): filter type, either sinc3 or sinc5
    """

    def __init__(self, spi_rack, module):
        """Inits D4 module class

        The D5a_module class needs an SPI_rack object at initiation. All
        communication will run via that class. At initialization the ADC filters
        will be set to 'sinc3' at 16.67 SPS.

        Args:
            spi_rack (SPI_rack object): SPI_rack class object via which the communication runs
            module (int): module number set on the hardware
        """
        self.module = module
        self.spi_rack = spi_rack

        self.reg = AD7175_registers

        self.filter_setting = None
        self.filter_type = None

        self._default_setup()

        for adc in range(0, 2):
            # Set filter to sinc3 and 16.67 SPS as default
            self.set_filter(adc, 'sinc3', 16)

    def set_filter(self, adc, filter_type, filter_setting):
        """Sets the ADC filter

        The two filter parameters determine the filter response (cutoff frequency),
        the 50 Hz rejection and the resolution. See the filter table on the website
        to determine which setting is correct for your application.

        Args:
            adc (int:0-1): ADC inside the module which needs to be set
            filter_type (string): set to sinc3 or sinc5
            filter_setting (int:0-20): the desired filter setting
        """
        filter_values = {'sinc3': 3, 'sinc5': 0}
        if filter_type not in filter_values:
            raise ValueError('Value {} does not exist. Possible values are: {}'.format(filter_type, filter_values))
        if filter_setting not in range(21):
            raise ValueError('Value {} not allowed. Possible values are from 0 to 20.'.format(filter_setting))

        self._write_data_16(adc, self.reg.FILTCON0_REG,
                            (filter_values[filter_type]<<self.reg.ORDER0) |
                            (filter_setting<<self.reg.ODR))

        self.filter_setting = filter_setting
        self.filter_type = filter_type

    def single_conversion(self, adc):
        """Perform a conversion

        Performs a conversion on the given ADC. It will both trigger the ADC and
        wait for the result. Because of this it will block all other operations.

        Args:
            adc (int:0-1): ADC to perform the conversion
        """
        # Reset filter
        self._write_data_16(adc, self.reg.adcMODE_REG, (0<<self.reg.MODE) | (1<<self.reg.SING_CYC))

        while True:
            status = self._read_data(adc, self.reg.STATUS_REG, 1)
            # if new data available:
            if (status[0]&0x80) == 0:
                # Get raw data, shift to correct place and convert to voltage
                raw_data = self._read_data(adc, self.reg.DATA_REG, 3)
                raw_data = raw_data[1:]
                raw_data_val = raw_data[0] << 16 | raw_data[1] << 8 | raw_data[2]

                # 2.5 Volt reference with factor 2 compensation for divider
                # gain set such that +-4V is full scale
                return (raw_data_val * 2 / 2**22) - 4.0

    def start_conversion(self, adc):
        """Trigger a conversion

        Triggers a conversion on the given ADC. Does not wait for the result. This
        should be used if multiple devices/adcs need triggering. After the conversion
        is done it will immediately continue doing conversions and updating the
        output.

        Args:
            adc (int:0-1): ADC to perform the conversion
        """
        # Reset filter
        self._write_data_16(adc, self.reg.adcMODE_REG, (0<<self.reg.MODE) | (1<<self.reg.SING_CYC))

    def get_result(self, adc):
        """Returns the result of a conversion

        Returns the result from a triggered conversion. The function will wait until the
        result is present, therefore it will block all other operations.

        It will return the last conversion result. If the time between the trigger and
        getting the result is too long, the result will be of a second/third conversion.
        The ADC keeps converting and updating the data output.

        Args:
            adc (int:0-1): ADC to readout
        Returns:
            ADC measured voltage (float)
        """
        while True:
            status = self._read_data(adc, self.reg.STATUS_REG, 1)
            # if new data available:
            if (status[0]&0x80) == 0:
                # Get raw data, shift to correct place and convert to voltage
                raw_data = self._read_data(adc, self.reg.DATA_REG, 3)
                raw_data = raw_data[1:]
                raw_data_val = raw_data[0] << 16 | raw_data[1] << 8 | raw_data[2]

                # 2.5 Volt reference with factor 2 compensation for divider
                return (raw_data_val * 2 / 2**22) - 4.0

    def offset_calibration(self, adc):
        """Offset voltage calibration routine

        Calibrates the offset of the given ADC input. To run this routine, put
        a short or 50 Ohm short on the input of the given ADC.

        Args:
            adc (int:0-1): ADC to calibrate
        """
        print('Make sure that ADC input {} is terminated with a short or 50 Ohm '
              'while running this calibration!'.format(adc+1))

        filter_setting = self.filter_setting
        filter_type = self.filter_type
        # set to best performance for offset calibration
        self.set_filter(adc, 'sinc3', 20)

        self._write_data_16(adc, self.reg.adcMODE_REG, (6<<self.reg.MODE) | (1<<self.reg.SING_CYC))
        running = True
        while running:
            status = self._read_data(adc, self.reg.STATUS_REG, 1)
            # if new data available:
            if (status[0]&0x80) == 0:
                running = False

        self._write_data_16(adc, self.reg.adcMODE_REG, (0<<self.reg.MODE) | (1<<self.reg.SING_CYC))

        # set to back to previous setting
        self.set_filter(adc, filter_type, filter_setting)

    def gain_calibration(self, adc):
        """Gain calibration routine

        Calibrates the gain of the given ADC input. To run this routine, put
        4V on the input of the given ADC using a D5a.

        Args:
            adc (int:0-1): ADC to calibrate
        """
        print('Make sure that ADC input {} is set to 4V (using a D5a)!'.format(adc+1))

        filter_setting = self.filter_setting
        filter_type = self.filter_type
        # set to best performance for offset calibration
        self.set_filter(adc, 'sinc3', 20)

        self._write_data_16(adc, self.reg.adcMODE_REG, (7<<self.reg.MODE) | (1<<self.reg.SING_CYC))
        running = True
        while running:
            status = self._read_data(adc, self.reg.STATUS_REG, 1)
            # if new data available:
            if (status[0]&0x80) == 0:
                running = False

        self._write_data_16(adc, self.reg.adcMODE_REG, (0<<self.reg.MODE) | (1<<self.reg.SING_CYC))

        # set to back to previous setting
        self.set_filter(adc, filter_type, filter_setting)

    def _default_setup(self):
        # Basic configuration
        for adc in range(0, 2):
            # Disable internal ref, set continuous conversion mode, internal clock and single cycle
            # Single cycle only outputs data when filter is settled
            self._write_data_16(adc, self.reg.adcMODE_REG,
                                (0<<self.reg.MODE) | (1<<self.reg.SING_CYC))
            self._write_data_16(adc, self.reg.IFMODE_REG, (1<<self.reg.DOUT_RESET))

            # Enable only channel 0, but set all to setup 0 and AIN4 as AINNEG
            # with respective AINPOS
            self._write_data_16(adc, self.reg.CH0_REG,
                                (1<<self.reg.CH_EN) |
                                (0<<self.reg.SETUP_SEL) |
                                (self.reg.AIN0<<self.reg.AINPOS) |
                                (self.reg.AIN4<<self.reg.AINNEG))

            self._write_data_16(adc, self.reg.CH1_REG,
                                (0<<self.reg.CH_EN) |
                                (0<<self.reg.SETUP_SEL) |
                                (self.reg.AIN1<<self.reg.AINPOS) |
                                (self.reg.AIN4<<self.reg.AINNEG))

            self._write_data_16(adc, self.reg.CH2_REG,
                                (0<<self.reg.CH_EN) |
                                (0<<self.reg.SETUP_SEL) |
                                (self.reg.AIN2<<self.reg.AINPOS) |
                                (self.reg.AIN4<<self.reg.AINNEG))

            self._write_data_16(adc, self.reg.CH3_REG,
                                (0<<self.reg.CH_EN) |
                                (0<<self.reg.SETUP_SEL) |
                                (self.reg.AIN3<<self.reg.AINPOS) |
                                (self.reg.AIN4<<self.reg.AINNEG))

            # Enable input buffers, disable reference buffers, external reference
            self._write_data_16(adc, self.reg.SETUPCON0_REG,
                                (1<<self.reg.BI_UNIPOLAR) |
                                (1<<self.reg.AINBUF0P) |
                                (1<<self.reg.AINBUF0M))

            # Set the gain such that +-4V is full scale. Can be overwritten by calibration
            self._write_data_24(adc, self.reg.GAIN0_REG, 6996273)
            self._write_data_24(adc, self.reg.GAIN1_REG, 6996273)
            self._write_data_24(adc, self.reg.GAIN2_REG, 6996273)
            self._write_data_24(adc, self.reg.GAIN3_REG, 6996273)

    def _read_data(self, adc, reg, no_bytes):
        """
        Read a given number of bytes (no_bytes) from given adc register
        """
        s_data = bytearray([reg | (1<<6)] + no_bytes*[0])
        r_i_data = self.spi_rack.read_data(self.module, adc, AD7175_MODE, AD7175_SPEED, s_data)

        return r_i_data

    def _write_data_8(self, adc, reg, data):
        s_data = bytearray([reg, data])
        self.spi_rack.write_data(self.module, adc, AD7175_MODE, AD7175_SPEED, s_data)

    def _write_data_16(self, adc, reg, data):
        s_data = bytearray([reg, data>>8, data&0xFF])
        self.spi_rack.write_data(self.module, adc, AD7175_MODE, AD7175_SPEED, s_data)

    def _write_data_24(self, adc, reg, data):
        s_data = bytearray([reg, data>>16, (data>>8)&0xFF, data&0xFF])
        self.spi_rack.write_data(self.module, adc, AD7175_MODE, AD7175_SPEED, s_data)

class AD7175_registers:
    """AD7175 register class

    A list of all the register names with values and all bits with corresponding
    locations in the registers.
    """
    # adc register locations
    STATUS_REG = 0x00
    adcMODE_REG = 0x01
    IFMODE_REG = 0x02
    REGCHECK_REG = 0x03
    DATA_REG = 0x04
    GPIOCON_REG = 0x06
    ID_REG = 0x07
    CH0_REG = 0x10
    CH1_REG = 0x11
    CH2_REG = 0x12
    CH3_REG = 0x13
    SETUPCON0_REG = 0x20
    SETUPCON1_REG = 0x21
    SETUPCON2_REG = 0x22
    SETUPCON3_REG = 0x23
    FILTCON0_REG = 0x28
    FILTCON1_REG = 0x28
    FILTCON2_REG = 0x28
    FILTCON3_REG = 0x28
    OFFSET0_REG = 0x30
    OFFSET1_REG = 0x30
    OFFSET2_REG = 0x30
    OFFSET3_REG = 0x30
    GAIN0_REG = 0x38
    GAIN1_REG = 0x38
    GAIN2_REG = 0x38
    GAIN3_REG = 0x38

    # Status Register bits
    nRDY = 7
    adc_ERROR = 6
    CRC_ERROR = 5
    REG_ERROR = 4
    CHANNEL = 0

    # adc Mode Register bits
    REF_EN = 15
    HIDE_DELAY = 14
    SING_CYC = 13
    DELAY = 8
    MODE = 4
    CLOCKSEL = 2

    # IFMODE Register bits
    ALT_SYNC = 12
    IOSTRENGTH = 11
    DOUT_RESET = 8
    CONTREAD = 7
    DATA_STAT = 6
    REG_CHECK = 5
    CRC_EN = 2
    WL16 = 0

    # GPIOCON Register bits
    MUX_IO = 12
    SYNC_EN = 11
    ERR_EN = 9
    ERR_DAT = 8
    IP_EN1 = 5
    IP_EN0 = 4
    OP_EN1 = 3
    OP_EN0 = 2
    GP_DATA1 = 1
    GP_DATA0 = 0

    # Channel Registers bits
    CH_EN = 15
    SETUP_SEL = 12
    AINPOS = 5
    AINNEG = 0

    # Setup Configuration Register bits
    BI_UNIPOLAR = 12
    REFBUF0P = 11
    REFBUF0M = 10
    AINBUF0P = 9
    AINBUF0M = 8
    REF_SEL = 4

    # Filter Configuration Register bits
    SINC3_MAP0 = 15
    ENHFILTEN = 11
    ENHFILT = 8
    ORDER0 = 5
    ODR = 0

    # adc register values
    AIN0 = 0
    AIN1 = 1
    AIN2 = 2
    AIN3 = 3
    AIN4 = 4
    REFP = 21
    REFN = 22
