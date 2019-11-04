"""IVVI module adapter B1b interface

SPI Rack interface code for the B1b IVVI module adapter. This is a purely break-in module:
it allows the user to connect to IVVI Rack sources left and right of the B1b module. The
routing of the front panel connectors to the x1 and x0.01 inputs can be set by software.

Example:
    Examples use: ::
        B1b = spirack.B1b_module(SPI_Rack1, 1, False)
"""

from .chip_mode import BICPINS_MODE, BICPINS_SPEED

class B1b_module(object):
    def __init__(self, spi_rack, module, reset=False):
        """B1b module interface class

        This class does the low level interfacing with the B1b module. When creating
        an instance it requires a SPI_rack class passed as a parameter.

        If reset is True, the module will be reset so all the switches are connected to the
        DAC MCX inputs. With reset is False, the software will read back the current setting.
        
        Args:
            module (int): the module number set by the user (most coincide with the hardware)
            reset (bool, optional): resets all the switch routing to the DAC inputs. Defaults to False.
        """
        self.spi_rack = spi_rack
        self.module = module
        
        if reset:
            self.reset()
        else:
            self.register = self.spi_rack.read_data(self.module, 6, BICPINS_MODE, BICPINS_SPEED, bytearray([0x0]))[0]
    
    def set_switch(self, location, switch, position):
        """Sets the given switch postition

        Sets the routing of the given switch. Each switch can be set to the corresponding DAC (MCX)
        input, or the isolated BNC input. The LED will indicate when the switch is connected to
        the isolated input.
        
        Args:
            location (string): location of the module switches to configure, either 'left' or 'right' 
            switch (string): which switch to set, either 'x1' or 'x0.01'
            position (string): route to DAC connector (MCX) or the isolated BNC, either 'DAC' or 'isolated'
        
        Raises:
            ValueError: if any of the inputs are not allowed
        """
        if location not in ['left', 'right']:
            raise ValueError('B1b module {}: location {} not allowed. Possible values are: {}'.format(
                self.module, location, ['left', 'right']))
        if switch not in ['x1', 'x0.01']:
            raise ValueError('B1b module {}: switch {} not allowed. Possible values are: {}'.format(
                self.module, switch, ['x1', 'x0.01']))
        
        position_values = {'DAC': 0, 'isolated': 1}
        if position not in position_values:
            raise ValueError('B1b module {}: position {} not allowed. Possible values are: {}'.format(
                self.module, position, [*position_values.keys()]))
        
        LUT = {('left', 'x1'): np.uint8(136), ('left', 'x0.01'): np.uint8(68), ('right', 'x1'): np.uint8(34), ('right', 'x0.01'): np.uint8(17)}
        value = LUT[(location, switch)]
        
        self.register &= ~value
        self.register |= (value*position_values[position])
        self.spi_rack.write_data(self.module, 5, BICPINS_MODE, BICPINS_SPEED, bytearray([self.register]))
    
    def get_switch(self, location, switch):
        """Gets the given switch postition

        Gets the routing of the given switch. Each switch can be set to the corresponding DAC (MCX)
        input, or the isolated BNC input. The LED will indicate when the switch is connected to
        the isolated input.
        
        Args:
            location (string): location of the module switches to configure, either 'left' or 'right' 
            switch (string): which switch to set, either 'x1' or 'x0.01'

        Raises:
            ValueError: if any of the inputs are not allowed
        
        Returns:
            Position of the switch: either 'DAC' or 'isolated'
        """
        if location not in ['left', 'right']:
            raise ValueError('B1b module {}: location {} not allowed. Possible values are: {}'.format(
                self.module, location, ['left', 'right']))
        if switch not in ['x1', 'x0.01']:
            raise ValueError('B1b module {}: switch {} not allowed. Possible values are: {}'.format(
                self.module, switch, ['x1', 'x0.01']))
        
        position_values = {0: 'DAC', 1: 'isolated'}
        LUT = {('left', 'x1'): 3, ('left', 'x0.01'): 2, ('right', 'x1'): 1, ('right', 'x0.01'): 0}
        shift = LUT[(location, switch)]
        
        rdata = self.spi_rack.read_data(self.module, 6, BICPINS_MODE, BICPINS_SPEED, bytearray([0x0]))[0]
        return position_values[(rdata >> shift) & 0x01]
    
    def reset(self):
        """Resets the switch position

        Resets all the switches to their default position: the DAC/MCX input.
        """
        self.register = 0

        self.spi_rack.write_data(self.module, 5, BICPINS_MODE, BICPINS_SPEED, bytearray([self.register]))