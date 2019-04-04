"""Current source module S4g interface

SPI Rack interface code for the S4g current source module.

Example:
    Example use: ::
        S4g = spirack.S4g_module(SPI_Rack1, 2, True)

Attributes:
    range_max_uni (int): Constant to set span to 0 to max mA
    range_max_bi (int): Constant to set span from -max mA to max mA
    range_min_bi (int): Constant to set span to -max/2 mA to max/2 mA

Todo:
    *Add checks on writing span and values
"""

import numpy as np

from .chip_mode import LTC2758_MODE, LTC2758_SPEED, LTC2758_RD_SPEED

class S4g_module(object):
    """S4g module interface class

    This class does the low level interfacing with the S4g module. When creating
    an instance it requires a SPI_rack class passed as a parameter. The analog
    span of the DAC module can be set via software for each of the 4 DACs/current
    sources

    Setting the current can happen via the set_current function. Other ways are
    the change_value_update function, which immediately updates the output of the
    DAC, or via the change_value function. This function writes the new value to
    the DAC but does not update the output until the update function is ran.

    Attributes:
        module (int): the module number set by the user (must coincide with hardware)
        span (list(int)): a list of values of the span for each DAC in the module
        currents (list(int)): a list of module current settings last written to the DAC
    """

    # DAC software span constants
    range_max_uni = 0
    range_max_bi = 2
    range_min_bi = 4

    # Mapping of virtual DACs/Current outputs to physical DAC ICs
    DAC_mapping = {0:7, 1:6, 2:3, 3:2}

    def __init__(self, spi_rack, module, max_current=50e-3, reset_currents=True):
        """Inits S4g module class

        The S4g_module class needs an SPI_rack object at initiation. All
        communication will run via that class. At initialization all the DACs
        in the module will be set to +-4V span and set to 0 Volt (midscale).
        This means all the current sources are reset to 0 mA with +-50mA range.

        Args:
            spi_rack (SPI_rack object): SPI_rack class object via which the communication runs
            module (int): module number set on the hardware
            current_range (float): maximum range of the S4g, configured in hardware
            reset_currents (bool): if True, then reset all currents to zero and
                                   change the span to `range_50mA_bi`
        """
        self.spi_rack = spi_rack
        self.module = module
        self.span = [np.NaN]*4
        self.currents = [np.NaN]*4
        self.max_current = max_current

        for i in range(4):
            self.currents[i], self.span[i] = self.get_settings(i)

        if reset_currents:
            for i in range(4):
                self.change_span(i, S4g_module.range_max_bi)
                self.set_current(i, 0.0)

    def change_span_update(self, DAC, span):
        """Changes the software span of selected DAC with update

        Changes the span of the DAC and immediately updates the output of
        the DAC

        Args:
            DAC (int: 0-3): Current output of which to change the span
            span (constant): values for the span as mentioned in the datasheet, use
                  constants as defined above
        """
        self.span[DAC] = span

        # Map output/virtual DAC to physical DAC IC
        DAC = S4g_module.DAC_mapping[DAC]

        # Determine which DAC in IC by checking even/uneven
        address = (DAC%2)<<1
        # Write and update span of DAC
        command = 0b0110

        # Data bytes
        b1 = (command<<4) | address
        b2 = 0
        b3 = span
        b4 = 0
        data = bytearray([b1, b2, b3, b4])

        # Determine in which IC the DAC is, for SPI chip select
        DAC_ic = DAC//2
        # send data via controller
        self.spi_rack.write_data(self.module, DAC_ic, LTC2758_MODE, LTC2758_SPEED, data)

    def change_span(self, DAC, span):
        """Changes the software span of selected DAC without update

        Changes the span of the DAC, but doesn't update the output value until
        update is called.

        Args:
            DAC (int: 0-3): Current output of which to change the span
            span (constant): values for the span as mentioned in the datasheet, use
                  constants as defined above
        """
        self.span[DAC] = span

        # Map output/virtual DAC to physical DAC IC
        DAC = S4g_module.DAC_mapping[DAC]

        # Determine which DAC in IC by checking even/uneven
        address = (DAC%2)<<1

        # Write span of DAC, doesn't update
        command = 0b0010

        # Data bytes
        b1 = (command<<4) | address
        b2 = 0
        b3 = span
        b4 = 0
        data = bytearray([b1, b2, b3, b4])

        # Determine in which IC the DAC is, for SPI chip select
        DAC_ic = DAC//2
        # send data via controller
        self.spi_rack.write_data(self.module, DAC_ic, LTC2758_MODE, LTC2758_SPEED, data)

    def update(self, DAC):
        """Updates the output of the DAC to the written value

        Updates the output of the DAC when called. Neccessary after using
        change_value or change_span when wanting to update the DAC.

        Args:
            DAC (int: 0-3): Current output of which to update
        """
        # Map output/virtual DAC to physical DAC IC
        DAC = S4g_module.DAC_mapping[DAC]

        # Determine which DAC in IC by checking even/uneven
        address = (DAC%2)<<1

        # Update DAC to given span/value
        command = 0b0100
        b1 = (command<<4) | address
        b2 = 0
        b3 = 0
        b4 = 0
        data = bytearray([b1, b2, b3, b4])

        # Determine in which IC the DAC is, for SPI chip select
        DAC_ic = DAC//2
        # send data via controller
        self.spi_rack.write_data(self.module, DAC_ic, LTC2758_MODE, LTC2758_SPEED, data)

    def change_value_update(self, DAC, value):
        """Changes and updates the DAC value

        Calling this function changes the value of the DAC and immediately
        updates the output.

        Args:
            DAC (int: 0-3): Current output of which to change the value
            value (18-bit unsigned int): new DAC value
        """
        # Map output/virtual DAC to physical DAC IC
        DAC = S4g_module.DAC_mapping[DAC]

        # Determine which DAC in IC by checking even/uneven
        address = (DAC%2)<<1

        # Write and update value of DAC
        command = 0b0111
        b1 = (command<<4) | address
        b2 = (value>>10) & 0xFF
        b3 = (value>>2) & 0xFF
        b4 = (value&0b11) << 6
        data = bytearray([b1, b2, b3, b4])

        # Determine in which IC the DAC is, for SPI chip select
        DAC_ic = DAC//2
        # send data via controller
        self.spi_rack.write_data(self.module, DAC_ic, LTC2758_MODE, LTC2758_SPEED, data)

    def set_current(self, DAC, current):
        """Sets the output current and updates the DAC output

        Calculates the DAC value for given current at the set span of the DAC.
        Will set to max/min when input current exceeds span and prints out a
        warning to the user. There will always be a difference between set
        current and output current as long as not a multiple of the step size
        is used. The calculated value is floored, not rounded.

        Args:
            DAC (int: 0-3): Current output of which to update the current
            current (float): new DAC current
        """
        step = self.get_stepsize(DAC)

        if self.span[DAC] == S4g_module.range_max_uni:
            bit_value = int(current / step)
            self.currents[DAC] = bit_value * step
            maxI = self.max_current
            minI = 0.0
        elif self.span[DAC] == S4g_module.range_max_bi:
            bit_value = int((current + self.max_current) / step)
            self.currents[DAC] = (bit_value * step) - self.max_current
            maxI = self.max_current
            minI = -self.max_current
        elif self.span[DAC] == S4g_module.range_min_bi:
            bit_value = int((current + (self.max_current/2.0)) / step)
            self.currents[DAC] = (bit_value * step) - (self.max_current/2.0)
            maxI = self.max_current/2.0
            minI = -(self.max_current/2.0)

        if current >= maxI:
            bit_value = (2**18)-1
            self.currents[DAC] = maxI
            print("Current too high for set span, DAC set to max value")
        elif current <= minI:
            self.currents[DAC] = minI
            bit_value = 0
            print("Current too low for set span, DAC set to min value")

        self.change_value_update(DAC, bit_value)

    def get_stepsize(self, DAC):
        """Returns the smallest current step for a given DAC

        Calculates and returns the smallest current step of the DAC for the
        set span. Current steps smaller than this will not change the DAC value.
        Recommended to only step the DAC in multiples of this value, as otherwise
        steps might not behave as expected.

        Args:
            DAC (int: 0-3): Current output of which the stepsize is calculated
        Returns:
            Smallest current step possible with DAC (float)
        """
        if self.span[DAC] == S4g_module.range_max_uni:
            return self.max_current/(2**18)
        if self.span[DAC] == S4g_module.range_max_bi:
            return self.max_current/(2**17)
        if self.span[DAC] == S4g_module.range_min_bi:
            return self.max_current/(2**18)

    def get_settings(self, DAC):
        """Reads current DAC settings

        Reads back the DAC registers of the given DAC for both the code
        and the span. Calculates the current set with the read out span.

        Args:
            DAC (int: 0-3): Current output of which the settings will be read
        Returns:
            List with currents and span: [current, span] (int)
        """
        # Map output/virtual DAC to physical DAC IC
        DAC = S4g_module.DAC_mapping[DAC]

        # Determine which DAC in IC by checking even/uneven
        address = (DAC%2)<<1
        # Determine in which IC the DAC is, for SPI chip select
        DAC_ic = DAC//2

        # Read code command
        command = 0b1101
        data = bytearray([(command<<4) | address, 0, 0, 0])

        code_data = self.spi_rack.read_data(self.module, DAC_ic, LTC2758_MODE, LTC2758_RD_SPEED, data)
        code = (code_data[1]<<10) | (code_data[2]<<2) | (code_data[3]>>6)

        # Read span command
        command = 0b1100
        data = bytearray([(command<<4) | address, 0, 0, 0])

        span_data = self.spi_rack.read_data(self.module, DAC_ic, LTC2758_MODE, LTC2758_RD_SPEED, data)
        span = span_data[2]

        if span == S4g_module.range_max_uni:
            current = (code*self.max_current/(2**18))
        elif span == S4g_module.range_max_bi:
            current = (code*self.max_current/(2**17)) - self.max_current
        elif span == S4g_module.range_min_bi:
            current = (code*self.max_current/(2**18)) - (self.max_current/2.0)
        else:
            raise ValueError("Span {} should not be used. Accepted values are: {}".format(span, [0, 2, 4]))

        return [current, span]
