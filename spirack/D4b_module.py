"""ADC module D4b interface

SPI Rack interface code for the ADC module. An 2 channel 24-bit ADC module
with integrated ARM Cortex M4 microcontroller. Used to connect to two neighbouring
IVVI rack modules. Is in hardware identical to the B2b module, the only difference
is the presence of connectors on the front of the module.

Example:
    Example use: ::
        D4b = spirack.D4b_module(SPI_Rack1, 1, True)
"""

import logging

from .B2b_module import B2b_module
from .chip_mode import SAMD51_MODE, SAMD51_SPEED

logger = logging.getLogger(__name__)

class D4b_module(B2b_module):    
    def __init__(self, spi_rack, module, calibrate=False):
        """D4b module interface class

        This class does the low level interfacing with the B2b module. When creating
        an instance it requires a SPI_rack class passed as a parameter.

        In contrast to the D4a module, a microcontroller in the module handles all the
        communication with the ADCs. This allows for exactly timed ADC updates: based
        on triggers, timers etc.

        Attributes:
            module (int): the module number set by the user (most coincide with the hardware)
            calibrate (bool): if True, runs calibration at initialisation
        """
        super().__init__(spi_rack, module, calibrate)
        self.type = 'D4b'

    def set_input_location(self, ADC, location):
        """Sets the location for the given ADC input

        Sets the ADC input location to back or front. Back is used to read out neighbouring
        IVVI rack modules.
        
        Args:
            ADC (int:0-1): channel of which to set the input location
            location (string): back or front
        """
        possible_values = {'back': 0, 'front': 1}
        if location not in possible_values:
            raise ValueError('{} module {}: value {} does not exist. Possible values '
                             'are: {}'.format(self.type, self.module, location, [*possible_values.keys()]))
        
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))
        
        command = self._command.ADC_LOCATION
        header = 128 | command.value
        length = 2
        wdata = bytearray([header, length, ADC, possible_values[location]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_input_location(self, ADC):
        """Gets the location for the given ADC
        
        Args:
            ADC (int:0-1): channel of which to get the input location
        
        Returns:
            input location of the ADC (string)
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))
        
        command = self._command.ADC_LOCATION
        wdata = bytearray([command.value, 1, ADC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        values = {0: 'back', 1: 'front'}
        return values[rdata[-1]]

    def set_input_connection(self, ADC, connection_type):
        """Sets the connection type for the given ADC input

        Sets the ADC input to either single ended or differential. For back connections to the
        IVVI Rack it should always be set to differential.
        
        Args:
            ADC (int:0-1): channel of which to set the connection type
            connection_type (string): single or differential
        """
        possible_values = {'single': 0, 'differential': 1}
        if connection_type not in possible_values:
            raise ValueError('{} module {}: value {} does not exist. Possible values '
                             'are: {}'.format(self.type, self.module, connection_type, [*possible_values.keys()]))
        
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))
        
        command = self._command.ADC_CONNECTION
        header = 128 | command.value
        length = 2
        wdata = bytearray([header, length, ADC, possible_values[connection_type]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_input_connection(self, ADC):
        """Gets the connection type for the given ADC
        
        Args:
            ADC (int:0-1): channel of which to get the connection type
        
        Returns:
            connection type of the ADC (string)
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))
        
        command = self._command.ADC_CONNECTION
        wdata = bytearray([command.value, 1, ADC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        values = {0: 'single', 1: 'differential'}
        return values[rdata[-1]]
