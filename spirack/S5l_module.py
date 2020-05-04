"""Trigger processor S5l module interface

SPI Rack interface code for the S5l module, a trigger processor with 2 trigger inputs
and 4 outputs. These outputs can be configured as a function of the two inputs.

"""

from .chip_mode import BICPINS_MODE, BICPINS_SPEED

import logging
logger = logging.getLogger(__name__)

class S5l_module(object):
    """S5l module interface class

    This class does the low level interfacing with the S5l module. When creating
    an instance it requires a SPI_rack class and a module number passed as a parameter.

    Attributes:
        module (int): the module number set by the user (must coincide with hardware)
    """

    def __init__(self, spi_rack, module, reset=False):
        """Inits S5l module class

        The S5l_module class needs an SPI_rack object at initiation. All
        communication will run via that class. At initialisation (if reset) the functionallity
        will be set to an 'or' function between the two inptus and the input reference
        voltage to 0.4 Volt.

        Args:
            spi_rack (SPI_rack object): SPI_rack class object via which the communication runs
            module (int): module number set on the hardware
            reset (bool): if True, then reset the module to 'or' functionality and 0.4V 
                          input reverence voltage
        """
        self.spi_rack = spi_rack
        self.module = module

        if reset:
            self._set_register(0)
            logger.info('S5l module %d: resetting the module at initialisation.', self.module)
    
    def set_functionality(self, function):
        """Sets the functionality of the module

        Sets the functionality of the module: how the two triggers are processed
        and how that sets the outputs. For a list of the functions and how they are
        mapped, see the module page on the SPI Rack website.

        Args:
            function (int): the function that the module should perform
        """
        possible_values = range(0,9)
        if function not in possible_values:
            raise ValueError('Value {} does not exist. Possible values are: {}'. format(function, possible_values))
        
        register = self._get_register()
        register &= 0b11100000
        register |= function
        
        self._set_register(register)
        
    def get_functionality(self):
        """Gets the set functionality

        Gets the set functionality directly from the module.

        Returns:
            The set functionality (int)
        """
        register = self._get_register()
        
        return register&0x1F
    
    def set_input_reference(self, voltage):
        """Sets the input reference voltage

        Sets the reference voltage on the input comparators.

        Args:
            voltage (float): reference voltage. Options: 0.4, 0.8, 1.6, 2.5
        """
        possible_values = {0.4:0, 0.8:1, 1.6:2, 2.5:3}
        if voltage not in possible_values:
            raise ValueError('Value {} Volt does not exist. Possible values are: {} Volt'.format(voltage, list(possible_values.keys())))
        
        register = self._get_register()
        register &= 0b00111111
        register |= (possible_values[voltage]<<6)
        
        self._set_register(register)
        
    def get_input_reference(self):
        """ Gets the input reference voltage

        Gets the reference voltage of the input comparators.

        Returns:
            The set input reference voltage.
        """
        register = self._get_register()
        DAC_val = register>>6
        
        mapping = {0:0.4, 1:0.8, 2:1.6, 3:2.5}
        return mapping[DAC_val]
    
    def set_invert_output(self, invert):
        """If set, inverts the functionallity of the logic outputs

        Whatever the set functionality, if this is set to True the output
        gets inverted.

        Args:
            invert (bool): inverts output if True
        """
        register = self._get_register()
        register &= 0b11011111
        register |= (invert<<5)
        
        self._set_register(register)
    
    def get_invert_output(self):
        """Gets if the output functionallity if inverted

        Returns:
            If the outputs are inverted (bool)
        """
        register = self._get_register() >> 5
        register &= 0x01
        return bool(register)
        
    def _set_register(self, data):
        """Sets the register

        For internal use only.
        """
        self.spi_rack.write_data(self.module, 5, BICPINS_MODE, BICPINS_SPEED, bytearray([data]))
    
    def _get_register(self):
        """Gets the register

        For internal use only.
        """
        register = self.spi_rack.read_data(self.module, 6, BICPINS_MODE, BICPINS_SPEED, bytearray([0]))
        return int.from_bytes(register, byteorder='big')