"""DAC module D5a interface

SPI Rack interface code for the D5a module.

Example:
    Example use: ::
        D5a = spirack.D5a_module(SPI_Rack1, 2, True)

Attributes:
    range_4V_uni (int): Constant to set span to 0V to 4V
    range_4V_bi (int): Constant to set span to -4V to 4V
    range_8V_uni (int): Constant to set span to 0V to 8V
    range_8V_bi (int): Constant to set span to -8V to 4V
    range_2V_bi (int): Constant to set span to -2V to 2V
"""

import time
import numpy as np

from .chip_mode import LTC2758_MODE, LTC2758_SPEED, LTC2758_RD_SPEED

class D5a_module(object):
    """D5a module interface class

    This class does the low level interfacing with the D5a module. When creating
    an instance it requires a SPI_rack class passed as a parameter. The analog
    span of the DAC module can be set via software for each of the 16 DACs
    individually.

    Setting the voltage can happen via the set_voltage function. Other ways are
    the change_value_update function, which immediately updates the output of the
    DAC, or via the change_value function. This function writes the new value to
    the DAC but does not update the output until the update function is ran.

    Attributes:
        module (int): the module number set by the user (must coincide with hardware)
        span (list(int)): a list of values of the span for each DAC in the module
        voltages (list(int)): a list of DAC voltage settings last written to the DAC
    """

    # DAC software span constants
    range_4V_uni = 0
    range_4V_bi = 2
    range_8V_uni = 1
    range_8V_bi = 3
    range_2V_bi = 4

    def __init__(self, spi_rack, module, reset_voltages=True, num_dacs=16):
        """Inits D5a module class

        The D5a_module class needs an SPI_rack object at initiation. All
        communication will run via that class. At initialization all the DACs
        in the module will be set to +-4V span and set to 0 Volt (midscale).

        Args:
            spi_rack (SPI_rack object): SPI_rack class object via which the communication runs
            module (int): module number set on the hardware
            reset_voltages (bool): if True, then reset all voltages to zero and
                                   change the span to `range_4V_bi`. If a voltage
                                   jump would occur, then ramp to zero in steps of 10 mV
            num_dacs (int): number of DAC channels available
        """
        self.spi_rack = spi_rack
        self.module = module
        self._num_dacs = num_dacs
        self.span = [np.NaN]*self._num_dacs
        self.voltages = [np.NaN]*self._num_dacs

        for i in range(self._num_dacs):
            self.voltages[i], self.span[i] = self.get_settings(i)

        if reset_voltages:
            for i in range(self._num_dacs):
                if np.abs(self.voltages[i])>1e-3:
                    # we need to ramp to zero first
                    print('D5a_module: ramping dac %d from %.3f V to zero' % (i, self.voltages[i]))
                    ramp_step = 10e-3
                    ramp_delay = 10e-3
                    steps = np.arange(0, self.voltages[i], np.sign(self.voltages[i])*ramp_step)[::-1]

                    for v in steps:
                        self.set_voltage(i, v)
                        time.sleep(ramp_delay)

                # Set all DACs to +-4V and midscale (0V)
                self.change_span(i, D5a_module.range_4V_bi)
                self.set_voltage(i, 0.0)

    def change_span_update(self, DAC, span):
        """Changes the software span of selected DAC with update

        Changes the span of the DAC and immediately updates the output of
        the DAC

        Note: changing the span is not thread safe!

        Args:
            DAC (int: 0-15): DAC inside the module of which to change the span
            span (constant): values for the span as mentioned in the datasheet, use
                  constants as defined above
        """
        self.span[DAC] = span

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

        Note: changing the span is not thread safe!

        Args:
            DAC (int: 0-15): DAC inside the module of which to change the span
            span (constant): values for the span as mentioned in the datasheet, use
                  constants as defined above
        """
        self.span[DAC] = span

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

    def change_value_update(self, DAC, value):
        """Changes and updates the DAC value

        Calling this function changes the value of the DAC and immediately
        updates the output.

        Args:
            DAC (int: 0-15): DAC inside the module of which to change the value
            value (18-bit unsigned int): new DAC value
        """
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

    def change_value(self, DAC, value):
        """Changes the DAC value

        Calling this function changes the value of the DAC, but does not
        update the output until an update is run.

        Args:
            DAC (int: 0-15): DAC inside the module of which to change the value
            value (18-bit unsigned int): new DAC value
        """
        # Determine which DAC in IC by checking even/uneven
        address = (DAC%2)<<1

        # Write value of DAC, don't update
        command = 0b0011
        b1 = (command<<4) | address
        b2 = value>>10
        b3 = (value>>2) & 0xFF
        b4 = (value&0b11) << 6
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
            DAC (int: 0-15): DAC inside the module of which to update
        """
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

    def set_voltage(self, DAC, voltage):
        """Sets the DAC output voltage and updates the DAC output

        Calculates the DAC value for given voltage at the set span of the DAC.
        Will set to max/min when input voltage exceeds span and prints out a
        warning to the user. There will always be a difference between set
        voltage and output voltage as long as not a multiple of the step size
        is used. The calculated value is floored, not rounded.

        Args:
            DAC (int: 0-15): DAC inside the module of which to update the voltage
            voltage (float): new DAC voltage
        """
        step = self.get_stepsize(DAC)

        if self.span[DAC] == D5a_module.range_4V_uni:
            bit_value = int(round(voltage / step))
            self.voltages[DAC] = bit_value * step
            maxV = 4.0
            minV = 0.0
        elif self.span[DAC] == D5a_module.range_4V_bi:
            bit_value = int(round((voltage + 4.0) / step))
            self.voltages[DAC] = (bit_value * step) - 4.0
            maxV = 4.0
            minV = -4.0
        if self.span[DAC] == D5a_module.range_8V_uni:
            bit_value = int(round(voltage / step))
            self.voltages[DAC] = bit_value * step
            maxV = 8.0
            minV = 0.0
        elif self.span[DAC] == D5a_module.range_8V_bi:
            bit_value = int(round((voltage + 8.0) / step))
            self.voltages[DAC] = (bit_value * step) - 8.0
            maxV = 8.0
            minV = -8.0
        elif self.span[DAC] == D5a_module.range_2V_bi:
            bit_value = int(round((voltage + 2.0) / step))
            self.voltages[DAC] = (bit_value * step) - 2.0
            maxV = 2.0
            minV = -2.0

        if voltage >= maxV:
            bit_value = (2**18)-1
            self.voltages[DAC] = maxV
            if voltage > maxV:
                print("Voltage too high for set span, DAC set to max value")
        elif voltage <= minV:
            self.voltages[DAC] = minV
            bit_value = 0
            if voltage < minV:
                print("Voltage too low for set span, DAC set to min value")

        self.change_value_update(DAC, bit_value)

    def get_stepsize(self, DAC):
        """Returns the smallest voltage step for a given DAC

        Calculates and returns the smalles voltage step of the DAC for the
        set span. Voltage steps smaller than this will not change the DAC value.
        Recommended to only step the DAC in multiples of this value, as otherwise
        steps might not behave as expected.

        Args:
            DAC (int: 0-15): DAC inside the module of which the stepsize is calculated
        Returns:
            Smallest voltage step possible with DAC (float)
        """
        if self.span[DAC] == D5a_module.range_4V_uni:
            return 4.0/(2**18)
        if self.span[DAC] == (D5a_module.range_4V_bi or D5a_module.range_8V_uni):
            return 8.0/(2**18)
        if self.span[DAC] == D5a_module.range_8V_bi:
            return 16.0/(2**18)
        if self.span[DAC] == D5a_module.range_2V_bi:
            return 4.0/(2**18)

    def get_settings(self, DAC):
        """Reads current DAC settings

        Reads back the DAC registers of the given DAC for both the code
        and the span. Calculates the voltage set with the read out span.

        Args:
            DAC (int: 0-15): DAC inside the module of which the settings will be read
        Returns:
            List with voltage and span: [voltages, span] (int)
        """
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

        if span == D5a_module.range_4V_uni:
            voltage = (code*4.0/(2**18))
        elif span == D5a_module.range_4V_bi:
            voltage = (code*8.0/(2**18)) - 4.0
        elif span == D5a_module.range_8V_uni:
            voltage = (code*8.0/(2**18))
        elif span == D5a_module.range_8V_bi:
            voltage = (code*16.0/(2**18)) - 8.0
        elif span == D5a_module.range_2V_bi:
            voltage = (code*4.0/(2**18)) - 2.0
        else:
            raise ValueError("Span {} should not be used. Accepted values are: {}".format(span, [0, 1, 2, 3, 4]))

        return [voltage, span]
