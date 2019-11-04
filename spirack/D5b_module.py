"""DAC module D5b interface

SPI Rack interface code for the D5b module. An 8 channel 18-bit DAC module
with integrated ARM Cortex M4 microcontroller.

Example:
    Example use: ::
        D5b = spirack.D5b_module(SPI_Rack1, 1, True)
"""

import logging

from enum import Enum
from time import sleep

import numpy as np

from .chip_mode import SAMD51_MODE, SAMD51_SPEED, BICPINS_MODE, BICPINS_SPEED

logger = logging.getLogger(__name__)

class D5b_module(object):
    """D5b module interface class

    This class does the low level interfacing with the D5b module. When creating
    an instance it requires a SPI_rack class passed as a parameter.

    In contrast to the D5a module, a microcontroller in the module handles all the
    communication with the DACs. This allows for exactly timed DAC updates: based
    on triggers, timers etc.

    Attributes:
        module (int): the module number set by the user (most coincide with the hardware)
    """

    def __init__(self, spi_rack, module, reset_voltages=True):
        self.spi_rack = spi_rack
        self.module = module

        self._command = D5b_Command

        if reset_voltages:
            for i in range(8):
                voltage = self.get_DAC_voltages(i)[0]
                if np.abs(voltage) > 1e-3:
                    logger.info("D5b module %d: ramping DAC %d from %.3fV to zero.",
                                self.module, i, voltage)
                    ramp_step = 10e-3
                    ramp_delay = 10e-3
                    steps = np.arange(0, voltage, np.sign(voltage)*ramp_step)[::-1]

                    for value in steps:
                        self.set_DAC_voltage(i, value)
                        sleep(ramp_delay)

                # Set all DACs to +-4V and midscale (0V)
                self.set_DAC_span(i, '4V_bi', update=False)
                self.set_DAC_voltage(i, 0.0, update=True)

    def set_clock_source(self, source):
        """Sets the clock source for the microcontroller

        Set the microcontroller clock source to either a local (inside the module)
        clock or a clock from the backplane. This allows for multiple modules to run
        of the same clock. The module expects a 10 MHz clock, either sine wave or square.

        Args:
            source (string): either 'internal' or 'external'. Clock source for the microcontroller
        """
        possible_values = {'internal':0, 'external':1}
        if source not in possible_values:
            raise ValueError('D5b module {}: value {} does not exist. Possible values '
                             'are: {}'.format(self.module, source, [*possible_values.keys()]))

        rw_bit = 1
        command = self._command.CLOCK_SOURCE
        header = (rw_bit<<7) | command.value
        length = 1
        wdata = bytearray([header, length, possible_values[source]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        sleep(0.1)
        if self.get_clock_source() != source:
            logger.error("D5b module %d: clock source not set to %s clock source!",
                         self.module, source)

    def get_clock_source(self):
        """Get the currently set clock source

        Gets the set clock source from the microcontroller.

        Returns:
            The set clock source: 'internal' or 'external' (string)
        """
        command = self._command.CLOCK_SOURCE
        wdata = bytearray([command.value, 1, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        values = {0:'internal', 1:'external'}
        return values[rdata[-1]]

    def set_DAC_span(self, DAC, span, update=True):
        """Changes the software span of the selected DAC

        Changes the span of the selected DAC. If update is True the span gets updated
        immediately. If False, it will update with the next span or value setting.

        Args:
            DAC (int: 0-7): DAC inside the module of which to set the span
            span (string): the span to be set (4V_uni, 8V_uni, 4V_bi, 8V_bi, 2V_bi)
            update (bool): if True updates the span immediately, if False updates
                           with the next span/value update
        """
        range_values = {'4V_uni':0, '8V_uni':1, '4V_bi':2, '8V_bi':3, '2V_bi':4}
        if span not in range_values:
            raise ValueError('D5b module {}: value {} not allowed for span. Possible values '
                             'are: {}'.format(self.module, span, [*range_values.keys()]))
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        rw_bit = 1
        command = self._command.DAC_SPAN

        header = (rw_bit<<7) | command.value
        length = 2
        wdata = bytearray([header, length, (update<<7)|DAC, range_values[span]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_DAC_span(self, DAC):
        """Gets the software span of the selected DAC

        Args:
            DAC (int: 0-7): DAC of which to read the span
        Returns:
            Set span of the DAC (string)
        """
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        command = self._command.DAC_SPAN
        wdata = bytearray([command.value, 1, DAC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        range_values = {0:'4V_uni', 1:'8V_uni', 2:'4V_bi', 3:'8V_bi', 4:'2V_bi'}
        return range_values[rdata[-1]]

    def set_DAC_mode(self, DAC, mode):
        """Sets the mode of the selected DAC

        The DACs can be set to two modes: 'DC' or 'toggle'. In DC mode the output of the DAC
        gets set statically and remains that way until the next update. In toggle mode the DAC
        gets toggled between two values. Multiple DACs can be set to toggle. Each DAC can have
        its own toggle values, but they always share the same toggle amount and toggle time.

        Args:
            DAC (int: 0-7): DAC of which to set the mode
            mode (string): mode of the DAC, either 'DC' or 'toggle'
        """
        possible_values = {'DC':0, 'toggle':1}
        if mode not in possible_values:
            raise ValueError('D5b module {}: value {} does not exist. Possible values '
                             'are: {}'.format(self.module, mode, [*possible_values.keys()]))
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        rw_bit = 1
        command = self._command.DAC_MODE

        header = (rw_bit<<7) | command.value
        length = 2
        wdata = bytearray([header, length, DAC, possible_values[mode]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_DAC_mode(self, DAC):
        """Gets the mode of the selected DAC

        Args:
            DAC (int: 0-7): DAC of which to read the mode
        Returns:
            The DAC mode (string)
        """
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        command = self._command.DAC_MODE
        wdata = bytearray([command.value, 1, DAC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        values = {0:'DC', 1:'toggle'}
        return values[rdata[-1]]

    def set_DAC_voltage(self, DAC, voltage, update=True):
        """Sets the voltage of the selected DAC

        Calculates and sets the DAC bit value using the set span and updates the DAC. The DAC value
        is the value which is output at all times, both in 'DC' and in 'toggle' mode.

        It will set the voltage to the max/min of the current span, if the input voltage exceeds
        these limits. Unless the user takes care of using a voltage which is an integere multiple
        of the DAC step size, the actual voltage will differ slightly from the requested one. For
        exact values, use the get_stepsize() function and use only integer multiples.

        Args:
            DAC (int: 0-7): DAC of which to set the voltage
            voltage (float): DAC output voltage
            update (bool): if True updates the output immediately, if False updates
                           with the next span/value update
        """
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        span = self.get_DAC_span(DAC)
        dat = self._calc_value_from_voltage(span, voltage)

        rw_bit = 1
        command = self._command.DAC_VALUE

        header = (rw_bit<<7) | command.value
        length = 4
        wdata = bytearray([header, length, (update<<7)|DAC, (dat>>16)&0xFF,
                           (dat>>8)&0xFF, dat&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def set_DAC_pos_toggle_voltage(self, DAC, voltage):
        """Sets the positive toggle voltage of the selected DAC

        Calculates and sets the DAC bit value for the positive toggle voltage. All the DACs which
        are set to 'toggle' mode will toggle between positive and negative toggle voltages. The
        DACs can have individually set positive, negative and normal voltages.

        Args:
            DAC (int: 0-7): DAC of which to set the voltage
            voltage (float): positive toggle voltage
        """
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        span = self.get_DAC_span(DAC)
        dat = self._calc_value_from_voltage(span, voltage)

        rw_bit = 1
        command = self._command.DAC_TOGGLE_POS

        header = (rw_bit<<7) | command.value
        length = 4
        wdata = bytearray([header, length, DAC, (dat>>16)&0xFF, (dat>>8)&0xFF, dat&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def set_DAC_neg_toggle_voltage(self, DAC, voltage):
        """Sets the negative toggle voltage of the selected DAC

        Calculates and sets the DAC bit value for the negative toggle voltage. All the DACs which
        are set to 'toggle' mode will toggle between positive and negative toggle voltages. The
        DACs can have individually set positive, negative and normal voltages.

        Args:
            DAC (int: 0-7): DAC of which to set the voltage
            voltage (float): negative toggle voltage
        """
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        span = self.get_DAC_span(DAC)
        dat = self._calc_value_from_voltage(span, voltage)

        rw_bit = 1
        command = self._command.DAC_TOGGLE_NEG

        header = (rw_bit<<7) | command.value
        length = 4
        wdata = bytearray([header, length, DAC, (dat>>16)&0xFF, (dat>>8)&0xFF, dat&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_DAC_voltages(self, DAC):
        """Reads the current DAC voltages

        Returns the currently set voltage, negative toggle voltage and positive toggle voltage
        of the given DAC.

        Args:
            DAC (int: 0-7): DAC of which to read the voltages
        Returns:
            List with voltages: [voltage, negative_toggle_voltage, positive_toggle_voltage]
        """
        if DAC not in range(8):
            raise ValueError('D5b module {}: DAC {} does not exist.'.format(self.module, DAC))

        span = self.get_DAC_span(DAC)

        command = self._command.DAC_VALUE
        wdata = bytearray([command.value, 3, DAC, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        bit_value = (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        voltage = self._calc_voltage_from_value(span, bit_value)

        command = self._command.DAC_TOGGLE_POS
        wdata = bytearray([command.value, 3, DAC, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        bit_value = (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        voltage_t_p = self._calc_voltage_from_value(span, bit_value)

        command = self._command.DAC_TOGGLE_NEG
        wdata = bytearray([command.value, 3, DAC, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        bit_value = (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        voltage_t_n = self._calc_voltage_from_value(span, bit_value)

        return (voltage, voltage_t_n, voltage_t_p)

    def set_trigger_holdoff_time(self, holdoff_time):
        """Sets the holdoff time from the trigger moment

        Sets the time the system waits after the trigger for outputting the toggling
        DACs. The mimimum time is 30 us, and the resolution is 100ns.

        Args:
            holdoff_time (seconds): amount of time to wait after trigger (minimum 30 us)
        """
        if holdoff_time < 30e-6:
            raise ValueError('D5b module {}: holdoff time {} seconds not allowed. '
                             'Has to be mimimum 30 us.'.format(self.module, holdoff_time))

        rw_bit = 1
        command = self._command.TRIGGER_HOLDOFF

        value = int((holdoff_time/100e-9) - 22)

        header = (rw_bit<<7) | command.value
        length = 4
        wdata = bytearray([header, length, (value>>24)&0xFF, (value>>16)&0xFF,
                           (value>>8)&0xFF, value&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_trigger_holdoff_time(self):
        """Gets the set trigger holdoff time

        See 'set_trigger_holdoff_time' for details.

        Returns:
            The set holdoff_time in seconds.
        """
        command = self._command.TRIGGER_HOLDOFF
        wdata = bytearray([command.value, 4, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        value = (rdata[-4]<<24) | (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        return round((value+22)*100e-9, 7)

    def set_toggle_time(self, toggle_time):
        """Sets the toggle time

        Sets the toggle time for all the DACs set to 'toggle' mode. The value set is
        the time how long the DAC stays high or low. It is a multiple of of the 100 ns
        clock used for the timing, this means sub 100 ns resolution is not possible.

        Args:
            value (float): toggle time in seconds (minimum 300ns)
        """
        if toggle_time < 5e-6:
            raise ValueError('D5b module {}: toggle time {} not allowed. '
                             'Has to be mimimum 5us.'.format(self.module, toggle_time))

        value = int(toggle_time/100e-9)
        if np.around(value*100e-9, 9) != toggle_time:
            raise ValueError('D5b module {}: toggle time {} not allowed. '
                             'Has to be a multiple of 100ns.'.format(self.module, toggle_time))

        rw_bit = 1
        command = self._command.TOGGLE_TIME

        header = (rw_bit<<7) | command.value
        length = 4
        wdata = bytearray([header, length, (value>>24)&0xFF, (value>>16)&0xFF,
                           (value>>8)&0xFF, value&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_toggle_time(self):
        """Gets the toggle time

        Gets the toggle time for all the DACs set to 'toggle' mode. See 'set_toggle_time'
        for more details.

        Returns:
            toggle time in seconds (float)
        """
        command = self._command.TOGGLE_TIME
        wdata = bytearray([command.value, 4, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        toggle_time = (rdata[-4]<<24) | (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        return np.around(toggle_time*100e-9,9)

    def set_toggle_amount(self, amount):
        """Sets the toggle amount

        Sets the amount of times the DACs (set to 'toggle mode') have to toggle. Generates
        a trigger on the backplane everytime the toggle happens. It has to be an even
        number of toggles.

        Args:
            amount (int): the amount of times the DACs have to toggle (even number)
        """
        if amount%2:
            raise ValueError('D5b module {}: amount {} not allowed, '
                             'has to be even number.'.format(self.module, amount))

        rw_bit = 1
        command = self._command.TOGGLE_AMOUNT

        header = (rw_bit<<7) | command.value
        length = 4
        wdata = bytearray([header, length, (amount>>24)&0xFF, (amount>>16)&0xFF,
                           (amount>>8)&0xFF, amount&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_toggle_amount(self):
        """Gets the toggle amount

        Returns:
            The toggle amount set (int)
        """
        command = self._command.TOGGLE_AMOUNT
        wdata = bytearray([command.value, 4, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        toggle_amount = (rdata[-4]<<24) | (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        return toggle_amount

    def cancel_run(self):
        """Stops the module once it's running

        When this function is called, it cancels the current run of the module. This can
        be useful if the toggle amount and/or the toggle time are set wrong and long.
        If the run gets cancelled, the status gets updated to reflect this.
        """
        logger.info("D5b module %d: cancelled run", self.module)

        rw_bit = 1
        command = self._command.CANCEL_CMD

        header = (rw_bit<<7) | command.value
        length = 1
        wdata = bytearray([header, length, 0])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_stepsize(self, span):
        """Returns the smallest voltage step for a given span

        Returns:
            Smallest voltage step possible with span (float)
        """
        range_values = ['4V_uni', '8V_uni', '4V_bi', '8V_bi', '2V_bi']

        if span not in range_values:
            raise ValueError('D5b module {}: value {} not allowed for span. '
                             'Possible values are: {}'.format(self.module, span, range_values))

        if span == '4V_uni':
            return 4.0/(2**18)
        if span in ('4V_bi', '8V_uni'):
            return 8.0/(2**18)
        if span == '8V_bi':
            return 16.0/(2**18)
        if span == '2V_bi':
            return 4.0/(2**18)

        return 8/(2**18)

    def _calc_voltage_from_value(self, span, bit_value):
        step = self.get_stepsize(span)

        if span in ('4V_uni', '8V_uni'):
            voltage = bit_value * step
        elif span == '4V_bi':
            voltage = (bit_value * step) - 4.0
        elif span == '8V_bi':
            voltage = (bit_value * step) - 8.0
        elif span == '2V_bi':
            voltage = (bit_value * step) - 2.0

        return voltage

    def _calc_value_from_voltage(self, span, voltage):
        step = self.get_stepsize(span)

        if span == '4V_uni':
            bit_value = int(round(voltage / step))
            voltage = bit_value * step
            maxV = 4.0
            minV = 0.0
        elif span == '4V_bi':
            bit_value = int(round((voltage + 4.0) / step))
            voltage = (bit_value * step) - 4.0
            maxV = 4.0
            minV = -4.0
        if span == '8V_uni':
            bit_value = int(round(voltage / step))
            voltage = bit_value * step
            maxV = 8.0
            minV = 0.0
        elif span == '8V_bi':
            bit_value = int(round((voltage + 8.0) / step))
            voltage = (bit_value * step) - 8.0
            maxV = 8.0
            minV = -8.0
        elif span == '2V_bi':
            bit_value = int(round((voltage + 2.0) / step))
            voltage = (bit_value * step) - 2.0
            maxV = 2.0
            minV = -2.0

        if voltage >= maxV:
            bit_value = (2**18)-1
            if voltage > maxV:
                logger.warning('D5b module %d: voltage too high for set span, '
                               'DAC set to max value: %f V', self.module, maxV)
                voltage = maxV
        elif voltage <= minV:
            bit_value = 0
            if voltage < minV:
                logger.warning('D5b module %d: voltage too low for set span, '
                               'DAC set to min value: %f V', self.module, minV)
                voltage = minV

        return bit_value

    def get_firmware_version(self):
        """Gets the firmware version of the S5b module

        Returns:
            firmware version of the S5b module (int)
        """
        command = self._command.GET_FW_VERSION
        wdata = bytearray([command.value, 1, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        return rdata[-1]
    
    def is_running(self):
        """Checks if the module is running

        This function return true if the module is running a measurement, should be used
        to check if data can be read.
        
        Returns:
            True if the module is running a measurement
        """

        data = self.spi_rack.read_data(self.module, 6, BICPINS_MODE, BICPINS_SPEED, bytearray([0]))
        return bool(data[0]&0x02)

    def _get_status(self):
        """Gets the status of the S5b

        Returns the status of the S5b. At bootup (before a first run) it will
        give 'booted'. This should not appear after. The status can be used to
        see if the module is done running.

        Returns:
            Status of the S5b (string)
        """
        command = self._command.STATUS_CMD
        wdata = bytearray([command.value, 1, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        values = {0:'running', 1:'finished', 2:'canceled', 3:'booted'}

        return values[rdata[-1]]

    def software_trigger(self):
        """Triggers the S5b

        This allows the user to trigger the S5b via software, not using the trigger lines
        on the backplane of the SPI rack.
        """
        command = self._command.SOFTWARE_TRIGGER
        header = 128 | command.value
        wdata = bytearray([header, 1, 0])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

class D5b_Command(Enum):
    """
    Commands used for communicating with the S5b module
    """
    CLOCK_SOURCE = 0
    TRIGGER_INPUT = 1
    TRIGGER_HOLDOFF = 2
    GET_FW_VERSION = 3
    GET_MODULE_NAME = 4
    DAC_SPAN = 5
    DAC_VALUE = 6
    DAC_TOGGLE_POS = 7
    DAC_TOGGLE_NEG = 8
    DAC_MODE = 9
    TOGGLE_TIME = 10
    TOGGLE_AMOUNT = 11
    STATUS_CMD = 12
    CANCEL_CMD = 13
    SOFTWARE_TRIGGER = 14
