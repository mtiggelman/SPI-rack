from spi_rack import *
from chip_mode import *

# DAC software span constants
range_4V_uni = 0
range_4V_bi = 2
range_2_5V_bi = 4

class D5a_module(object):
    """D5a module interface class

    This class does the low level interfacing with the D5a module. When creating
    an instance it requires a SPI_rack class passed as a parameter. The analog
    span of the DAC module can be set via software for each of the 16 DACs
    individually.

    Changing the voltage can happen via change_value_update, which immediately
    updates the output of the DAC, or via the change_value function. This
    function writes the new value to the DAC but does not update the output
    until the update function is ran.

    Attributes:
        module: the module number set by the user (must coincide with hardware)
        span: a list of values of the span for each DAC in the module
        voltages: a list of DAC voltage settings last written to the DAC
    """

    def __init__(self, spi_rack, module):
        """Inits D5a module class

        The D5a_module class needs an SPI_rack object at initiation. All
        communication will run via that class. At initialization all the DACs
        in the module will be set to +-4V span and set to 0 Volt (midscale).

        Args:
            spi_rack: SPI_rack class object via which the communication runs
            module: module number set on the hardware
        Example:
            D5a_1 = D5a_module(SPI_Rack_1, 4)
        """
        self.spi_rack = spi_rack
        self.module = module
        self.span = [0]*16
        self.voltages = [0]*16

        for i in range(16):
            # Set all DACs to +-4V and midscale (0V)
            self.change_span(i, range_4V_uni)
            self.set_voltage(i, 0.0)

    def change_span_update(self, DAC, span):
        """Changes the software span of selected DAC with update

        Changes the span of the DAC and immediately updates the output of
        the DAC

        Args:
            DAC: DAC inside the module to change the span of (int: 0-15)
            span: values for the span as mentioned in the datasheet, use
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
        self.spi_rack.writeData(self.module, DAC_ic, LTC2758_MODE, data)

    def change_span(self, DAC, span):
        """Changes the software span of selected DAC without update

        Changes the span of the DAC, but doesn't update the output value until
        update is called.

        Args:
            DAC: DAC inside the module to change the span of (int: 0-15)
            span: values for the span as mentioned in the datasheet, use
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
        self.spi_rack.writeData(self.module, DAC_ic, LTC2758_MODE, data)

    def change_value_update(self, DAC, value):
        """Changes and updates the DAC value

        Calling this function changes the value of the DAC and immediately
        updates the output.

        Args:
            DAC: DAC inside module to change value of (int: 0-15)
            value: new DAC value (18-bit unsigned integer)
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
        self.spi_rack.writeData(self.module, DAC_ic, LTC2758_MODE, data)

    def change_value(self, DAC, value):
        """Changes the DAC value

        Calling this function changes the value of the DAC, but does not
        update the output until an update is run.

        Args:
            DAC: DAC inside module to change value of (int: 0-15)
            value: new DAC value (18-bit unsigned integer)
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
        self.spi_rack.writeData(self.module, DAC_ic, LTC2758_MODE, data)

    def update(self, DAC):
        """Updates the output of the DAC to the written value

        Updates the output of the DAC when called. Neccessary after using
        change_value or change_span when wanting to update the DAC.

        Args:
            DAC: DAC inside module to change value of (int: 0-15)
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
        self.spi_rack.writeData(self.module, DAC_ic, LTC2758_MODE, data)

    def set_voltage(self, DAC, voltage):
        """Sets the DAC output voltage and updates the DAC output

        Calculates the DAC value for given voltage at the set span of the DAC.
        Will set to max/min when input voltage exceeds span and prints out a
        warning to the user. There will always be a difference between set
        voltage and output voltage as long as not a multiple of the step size
        is used. The calculated value is floored, not rounded.

        Args:
            DAC: DAC inside module to update voltage of (int: 0-15)
            voltage: new DAC voltage (float)
        """
        self.voltages[DAC] = voltage

        if self.span[DAC] == range_4V_uni:
            a = (2**18-1)/4.0
            b = 0
            maxV = 4.0
            minV = 0.0
        elif self.span[DAC] == range_4V_bi:
            a = (2**18-1)/8.0
            b = 2**17
            maxV = 4.0
            minV = -4.0
        elif self.span[DAC] == range_2_5V_bi:
            a = (2**18-1)/5.0
            b = 2**17
            maxV = 2.5
            minV = -2.5

        if voltage > maxV:
            voltage = maxV
            print("Voltage too high for set span, set to max value")
        elif voltage < minV:
            voltage = minV
            print("Voltage too low for set span, set to min value")

        bit_value = int(a*voltage + b)
        self.change_value_update(DAC, bit_value)

    def get_stepsize(self, DAC):
        """Returns the smallest voltage step for a given DAC

        Calculates and resturns the smalles voltage step of the DAC for the
        set span. Voltage steps smaller than this will not change the DAC value.
        Recommended to only step the DAC in multiples of this value, as otherwise
        steps might not behave as expected.

        Args:
            DAC: DAC of which the step size is calculated (int: 0-15)
        Returns:
            Smallest voltage step possible with DAC (float)
        """
        if self.span[DAC] == range_4V_uni:
            return 4.0/(2**18)
        if self.span[DAC] == range_4V_bi:
            return 8.0/(2**18)
        if self.span[DAC] == range_2_5V_bi:
            return 5.0/(2**18)
