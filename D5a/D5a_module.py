from spi_rack import *
import future

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

        for i in range(16):
            # Set all DACs to +-4V and midscale (0V)
            self.change_span(i, range_4V_uni)
            self.change_value(i, 2**17)
            self.update(i)

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
        DAC_ic = DAC/2
        # send data via controller
        self.spi_rack.writeData(self.module, DAC_ic, data)

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
        DAC_ic = DAC/2
        # send data via controller
        self.spi_rack.writeData(self.module, DAC_ic, data)

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
        DAC_ic = DAC/2
        # send data via controller
        self.spi_rack.writeData(self.module, DAC_ic, data)

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
        DAC_ic = DAC/2
        # send data via controller
        self.spi_rack.writeData(self.module, DAC_ic, data)

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
        DAC_ic = DAC/2
        # send data via controller
        self.spi_rack.writeData(self.module, DAC_ic, data)
