"""Cryomux control U2 module interface

SPI Rack interface code for the U2 module, which controls the data going
to the shift registers of the cryomux.

"""

import numpy as np

from .D5a_module import D5a_module
from .chip_mode import CRYOMUX_MODE, CRYOMUX_SPEED

class U2_module(D5a_module):
    """U2 module interface class

    This class does the low level interfacing with the U2 module. When creating
    an instance it requires a SPI_rack class and a module number passed as a parameter.
    It is a child class of the D5a_module class, so it has all the same functions and
    attributes. Inside the module is one of the D5a DAC pcbs.

    Attributes:
        module (int): the module number set by the user (must coincide with hardware)
        span (list(int)): a list of values of the span for each DAC in the module
        voltages (list(int)): a list of DAC voltage settings last written to the DAC
        active_mux (int): the mux that is currently selected
    """

    #DAC mapping, function to DAC number:
    DAC_switch_pos = 7
    DAC_switch_neg = 6
    DAC_register_pos = 3
    DAC_register_neg = 2
    DAC_data_pos = 4
    DAC_data_neg = 5
    DAC_comp_volt = 1

    def __init__(self, spi_rack, module, reset_voltages=True):
        """Inits U2 module class

        The U2_module class needs an SPI_rack object at initiation. All
        communication will run via that class. At initialization all the DACs
        in the module will be set to +-4V span and set to 0 Volt (midscale).

        Args:
            spi_rack (SPI_rack object): SPI_rack class object via which the communication runs
            module (int): module number set on the hardware
            reset_voltages (bool): if True, then reset all voltages to zero and
                                   change the span to `range_4V_bi`. If a voltage
                                   jump would occur, then ramp to zero in steps of 10 mV
        """
        # init from D5a with 8 DACs
        D5a_module.__init__(self, spi_rack=spi_rack, module=module,
                            reset_voltages=reset_voltages, num_dacs=8)

        self.active_mux = np.NaN

    def set_switch_supply(self, voltages):
        """Sets the supply voltages for the switches

        Args:
            voltages (float): list of positive and negative supply voltage for the
                              switches: [pos_voltage, neg_voltage]
        """
        self.set_voltage(U2_module.DAC_switch_pos, voltages[0])
        self.set_voltage(U2_module.DAC_switch_neg, voltages[1])

    def get_switch_supply(self):
        """Gets the current switch supply voltages

        Returns:
            List of switch supply voltages (float): [pos_voltage, neg_voltage]
        """
        return [self.voltages[U2_module.DAC_switch_pos],
                self.voltages[U2_module.DAC_switch_neg]]

    def set_register_supply(self, voltages):
        """Sets the supply voltages for the shift registers

        Args:
            voltages (float): list of positive and negative supply voltage for the
                              shift registers: [pos_voltage, neg_voltage]
        """
        self.set_voltage(U2_module.DAC_register_pos, voltages[0])
        self.set_voltage(U2_module.DAC_register_neg, voltages[1])

    def get_register_supply(self):
        """Gets the current shift register supply voltages

        Returns:
            List of shift register supply voltages (float): [pos_voltage, neg_voltage]
        """
        return [self.voltages[U2_module.DAC_register_pos],
                self.voltages[U2_module.DAC_register_neg]]

    def set_data_levels(self, voltages):
        """Sets the data high/low voltages

        These voltages correspond to the digital high/low values. Also sets
        the comparator level to midway between these values.

        Args:
            voltages (float): list of voltages corresponding to the low and high
                              data voltages: [low_voltage, high_voltage]
        """
        self.set_voltage(U2_module.DAC_data_pos, voltages[0])
        self.set_voltage(U2_module.DAC_data_neg, voltages[1])

        self.set_comparator_level(np.mean(voltages))

    def get_data_levels(self):
        """Gets the currently set data voltages

        Returns:
            List of data voltages (float): [low_voltage, high_voltage]
        """
        return [self.voltages[U2_module.DAC_data_pos],
                self.voltages[U2_module.DAC_data_neg]]

    def set_comparator_level(self, voltage):
        """Sets the comparator for data readback

        The data being send back is toggled between the two supply levels of the
        shift register. These are voltages that the SPI Rack is not familiar with.
        A comparator is placed on the input to translate these levels back to 0-3.3V.

        Args:
            voltage (float): voltage around which the decision for low/high is made
        """
        self.set_voltage(U2_module.DAC_comp_volt, voltage)

    def get_comparator_level(self):
        """Gets the currently set comparator voltage

        Returns:
            Comparator voltage (float)
        """
        return self.voltages[U2_module.DAC_comp_volt]

    def select_mux(self, mux):
        """Activates the selected mux

        Writes the correct SPI code to the shift registers to select the desired
        mux.

        Args:
            mux (int): select mux 1 to 16
        """
        if mux not in range(1, 17):
            raise ValueError('Mux {} not allowed. Possible values are 1 to 16'.format(mux))

        self.active_mux = mux
        # mux ranges from 1 to 16
        data = 1 << (mux-1)
        s_data = bytearray([(data>>8)&0xFF, data&0xFF])
        # set cryomux shift registers to spi 7
        self.spi_rack.write_data(self.module, 7, CRYOMUX_MODE, CRYOMUX_SPEED, s_data)
