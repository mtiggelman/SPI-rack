"""ADC module B2b interface

SPI Rack interface code for the ADC module. An 2 channel 24-bit ADC module
with integrated ARM Cortex M4 microcontroller. Used to connect to two neighbouring
IVVI rack modules

Example:
    Example use: ::
        B2b = spirack.B2b_module(SPI_Rack1, 1, True)
"""

import logging

from enum import Enum
from time import sleep

import numpy as np

from .chip_mode import SAMD51_MODE, SAMD51_SPEED, BICPINS_MODE, BICPINS_SPEED

logger = logging.getLogger(__name__)

class B2b_module(object):
    def __init__(self, spi_rack, module, calibrate=False):
        """B2b module interface class

        This class does the low level interfacing with the B2b module. When creating
        an instance it requires a SPI_rack class passed as a parameter.

        In contrast to the D4a module, a microcontroller in the module handles all the
        communication with the ADCs. This allows for exactly timed ADC updates: based
        on triggers, timers etc.

        Attributes:
            module (int): the module number set by the user (most coincide with the hardware)
            calibrate (bool): if True, runs calibration at initialisation
        """
        self.spi_rack = spi_rack
        self.module = module
        self.type = 'B2b'

        self.sample_time = {'sinc3':sinc3_sample_time, 'sinc5': sinc5_sample_time}

        self._command = B2b_Command

        if calibrate:
            self.calibrate()

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
            raise ValueError('{} module {}: value {} does not exist. Possible values '
                             'are: {}'.format(self.type, self.module, source, [*possible_values.keys()]))

        command = self._command.CLOCK_SOURCE
        header = 128 | command.value
        length = 1
        wdata = bytearray([header, length, possible_values[source]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        sleep(0.1)
        if self.get_clock_source() != source:
            logger.error("%s module %d: clock source not set to %s clock source!",
                         self.type, self.module, source)

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

    def calibrate(self):
        """Run calibration routine

        This will run a gain and offset calibration routine on the B2b module. The
        function will stall until the routine is finished.
        """
        command = self._command.ADC_CALIBRATE
        header = (1<<7) | command.value
        length = 1
        wdata = bytearray([header, length, 0])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
        logger.info(' %s module %d: Starting calibration...', self.type, self.module)
        print(' {} module {}: Starting calibration...'.format(self.type, self.module))
        sleep(4)
        logger.info(' %s module %d: Finished calibration...', self.type, self.module)
        print(' {} module {}: Finished calibration...'.format(self.type, self.module))
    
    def is_running(self):
        """Checks if the module is running

        This function return true if the module is running a measurement, should be used
        to check if data can be read.
        
        Returns:
            True if the module is running a measurement
        """

        data = self.spi_rack.read_data(self.module, 6, BICPINS_MODE, BICPINS_SPEED, bytearray([0]))
        return bool(data[0]&0x01)

    def _get_status(self):
        """Gets the status

        Returns the status of the module. At bootup (before a first run) it will
        give 'booted'. This should not appear after. The status can be used to
        check where the module is in the process. Do not us this function to check
        if the module is done running.

        Returns:
            Status of the module (string)
        """
        command = self._command.STATUS_CMD
        wdata = bytearray([command.value, 1, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
        values = {0:'running', 1:'idle', 2:'waiting', 3:'booted', 4:'readout', 5:'cancelled', 6:'done'}
        return values[rdata[-1]]

    def set_trigger_amount(self, trigger_amount):
        """Sets the amount of triggers expected
        
        Args:
            trigger_amount (int): amount of triggers
        """

        command = self._command.TRIGGER_AMOUNT

        header = 128 | command.value
        length = 4
        wdata = bytearray([header, length, (trigger_amount>>24)&0xFF, (trigger_amount>>16)&0xFF, (trigger_amount>>8)&0xFF, trigger_amount&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def get_trigger_amount(self):
        """Gets the amount of triggers expected
        
        Returns:
            amount of triggers 
        """

        command = self._command.TRIGGER_AMOUNT
        wdata = bytearray([command.value, 4, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
        trigger_amount = (rdata[-4]<<24) | (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        return trigger_amount

    def set_sample_amount(self, ADC, sample_amount):
        """Sets the amount of samples per trigger

        Sets the amount of samples that the ADC channel takes per trigger.
        
        Args:
            ADC (int:0-1): channel to set the sample amount of
            sample_amount (int): amount of samples per trigger
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        command = self._command.ADC_SAMPLE_AMOUNT
        
        header = 128 | command.value
        length = 5
        wdata = bytearray([header, length, ADC, (sample_amount>>24)&0xFF, (sample_amount>>16)&0xFF, (sample_amount>>8)&0xFF, sample_amount&0xFF])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
    def get_sample_amount(self, ADC):
        """Gets the amount of samples per trigger

        Gets the amount of samples that the ADC channel takes per trigger.
        
        Args:
            ADC (int:0-1): channel of which to get the sample amount
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        command = self._command.ADC_SAMPLE_AMOUNT
        wdata = bytearray([command.value, 4, ADC, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
        sample_amount = (rdata[-4]<<24) | (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        return sample_amount

    def get_firmware_version(self):
        """Gets the firmware version of the module

        Returns:
            firmware version of the module (int)
        """
        command = self._command.GET_FW_VERSION
        wdata = bytearray([command.value, 1, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        return rdata[-1]

    def set_ADC_enable(self, ADC, enable):
        """Enables given ADC channel

        Args:
            ADC (int:0-1): channel to activate
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        if enable not in range(2):
            raise ValueError('{} module {}: {} not a valid input. Should be a boolean'.format(self.type, self.module, enable))
            
        command = self._command.ADC_ENABLE
        header = 128 | command.value
        length = 2
        wdata = bytearray([header, length, ADC, enable])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
    def get_ADC_enable(self, ADC):
        """Gets status of ADC channel

        Args:
            ADC (int:0-1): ADC of which to get the status
        Returns:
            status of ADC channel
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        command = self._command.ADC_ENABLE
        wdata = bytearray([command.value, 1, ADC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        return rdata[-1]

    def software_trigger(self):
        """Triggers the ADC module

        Sends a software trigger to the ADC module to take the amount of samples specified by
        `set_sample_amount`. This can be used for example to take standalone measurements or to
        take an FFT measurement.
        """

        command = self._command.SOFTWARE_TRIGGER
        header = 128 | command.value
        wdata = bytearray([header, 1, 0])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def _get_ADC_data_loc(self, ADC):
        """Gets data location of final byte of last sample

        Only for internal use!
        """
        command = self._command.DATA_LOC
        wdata = bytearray([command.value, 4, ADC, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
        data_loc = (rdata[-4]<<24) | (rdata[-3]<<16) | (rdata[-2]<<8) | (rdata[-1])
        return data_loc

    def get_data(self):
        """Reads back all the data from the module

        Returns:
            ADC0, ADC1: numpy arrays of float. None if ADC is not enabled
        """
        ADC0, ADC1 = None, None
        
        if self.get_ADC_enable(0):
            # Get location of the last data byte in SRAM
            max_data_location = self._get_ADC_data_loc(0)
            # Create array with readout locations, for max 120 bytes at a time
            # Start location for ADC 0 is 0
            locations = np.arange(0, max_data_location, 120)
            
            # Array with amounts of bytes per readout
            amounts = np.zeros_like(locations)
            amounts[:-1] = locations[1:] - locations[:-1]
            amounts[-1] = max_data_location - locations[-1]
            
            ADC0 = np.zeros(int(max_data_location/3))
            
            # Readback the data in steps of max 120 bytes
            for i, loc in enumerate(locations):
                command = self._command.READ_LOC
                header = 128 | command.value
                wdata = bytearray([header, 4, (loc>>16)&0xFF, (loc>>8)&0xFF, loc&0xFF, amounts[i]])
                self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
                
                sleep(0)

                command = self._command.GET_DATA
                wdata = bytearray([command.value, amounts[i], 0, 0xFF]+[0xFF]*amounts[i])
                rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

                j=int(loc/3)
                for n in range(4,len(rdata),3):
                    # Shift data in correct order
                    ADC0[j] = (rdata[n]<<16 | rdata[n+1]<<8 | rdata[n+2])
                    j+=1
            
            # Calculate the ADC values
            ADC0 = (ADC0*8.192/2**23) - 8.192
        
        if self.get_ADC_enable(1):
            # Get location of the last data byte in SRAM
            max_data_location = self._get_ADC_data_loc(1)
            # Create array with readout locations, for max 120 bytes at a time
            # Start location for ADC 1 is 65536
            locations = np.arange(62500, max_data_location, 120)
            
            # Array with amounts of bytes per readout
            amounts = np.zeros_like(locations)
            amounts[:-1] = locations[1:] - locations[:-1]
            amounts[-1] = max_data_location - locations[-1]
            
            ADC1 = np.zeros(int((max_data_location-62500)/3))

            # Readback the data in steps of max 120 bytes
            for i, loc in enumerate(locations):
                command = self._command.READ_LOC
                header = 128 | command.value
                wdata = bytearray([header, 4, (loc>>16)&0xFF, (loc>>8)&0xFF, loc&0xFF, amounts[i]])
                self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
                
                sleep(0)

                command = self._command.GET_DATA
                wdata = bytearray([command.value, amounts[i], 0, 0xFF]+[0xFF]*amounts[i])
                rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

                j=int((loc-62500)/3)
                for n in range(4,len(rdata),3):
                    # Shift data in correct order
                    ADC1[j] = (rdata[n]<<16 | rdata[n+1]<<8 | rdata[n+2])
                    j+=1

            # Calculate the ADC values
            ADC1 = (ADC1*8.192/2**23) - 8.192
        
        return ADC0, ADC1  

    def cancel(self):
        """Stops the module once it's running

        When this function is called, it cancels the current run of the module. This can
        be useful if the toggle amount and/or the toggle time are set wrong and long.
        If the run gets cancelled, the status gets updated to reflect this.
        """

        logger.info("%s module %d: cancelled measuring", self.type, self.module)
        print("{} module {}: cancelled measuring".format(self.type, self.module))

        command = self._command.CANCEL_CMD

        header = 128 | command.value
        length = 1
        wdata = bytearray([header, length, 0])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

    def set_trigger_holdoff_time(self, holdoff_time):
        """Sets the holdoff time from the trigger moment

        Sets the time the system waits after the trigger with a resolution of 100ns.

        Args:
            holdoff_time (seconds): amount of time to wait after
        """
        # if holdoff_time < 30e-6:
        #     raise ValueError('{} module {}: holdoff time {} seconds not allowed. '
        #                      'Has to be mimimum 30 us.'.format(self.type, self.module, holdoff_time))

        value = int((holdoff_time/100e-9))
        
        command = self._command.TRIGGER_HOLDOFF
        header = 128 | command.value
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
        return round((value)*100e-9, 7)

    def set_filter_rate(self, ADC, filter_rate):
        """Sets the ADC filter

        The filter rate (together with the filter type) determines the cutoff frequency, 
        sample rate, the resolution and the 50 Hz rejection. See the filter table to 
        determine which setting to use.
        
        Args:
            ADC (int:0-1): ADC of which to change the filter
            filter_rate (int:0-20): the desired filter setting
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))
        if filter_rate not in range(21):
            raise ValueError('{} module {}: filter rate {} is not allowed.'.format(self.type, self.module, filter_rate))

        command = self._command.ADC_FILTER_RATE
        header = 128 | command.value
        length = 2
        wdata = bytearray([header, length, ADC, filter_rate])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
    def get_filter_rate(self, ADC):
        """Gets the ADC filter

        Returns the ADC filter setting of the given ADC. See the filter table to interpret the result.
        
        Args:
            ADC (int:0-1): ADC of which to get the filter
        
        Returns:
            filter_rate (int): the current filter setting
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        command = self._command.ADC_FILTER_RATE
        wdata = bytearray([command.value, 1, ADC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata) 
        return rdata[-1]
    
    def set_filter_type(self, ADC, filter_type):
        """Set the filter type

        The ADC filter can be set to two different types: 'sinc3' or 'sinc5'. The filter type 
        determines (with the filter rate) the cutoff frequency, sample rate, the resolution 
        and the 50 Hz rejection. See the filter table to determine which setting is correct 
        for your application.
        
        Args:
            ADC (int:0-1): ADC of which to set the filter type
            filter_type (string): possible values are 'sinc3' or 'sinc5'
        """

        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))
        possible_values = {'sinc3':3, 'sinc5':0}
        if filter_type not in possible_values:
            raise ValueError('{} module {}: filter type {} does not exist. Possible values '
                             'are: {}'.format(self.type, self.module, filter_type, [*possible_values.keys()]))

        command = self._command.ADC_FILTER_TYPE
        header = 128 | command.value
        length = 2
        wdata = bytearray([header, length, ADC, possible_values[filter_type]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
    def get_filter_type(self, ADC):
        """Gets the filter type

        Returns the filter type of the given ADC.
        
        Args:
            ADC (int:0-1): ADC of which to get the filter
        
        Returns:
            filter_type (string): the current filter type
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        command = self._command.ADC_FILTER_TYPE
        wdata = bytearray([command.value, 1, ADC, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata) 
        
        type_values = {0:'sinc5', 3:'sinc3'}
        return type_values[rdata[-1]]
    
    def set_trigger_input(self, trigger):
        """Sets the trigger input location

        Sets the trigger input location for the ADC module. If it is set to 'None', no external
        triggers will start the module: it will only start via the `software_trigger` function.
        Otherwise it will trigger on rising edges from either the controller module or the D5b.
        
        Args:
            trigger (string): the input location
        """
        possible_values = {'None':0, 'Controller':1, 'D5b':2}
        if trigger not in possible_values:
            raise ValueError('{} module {}: trigger source {} does not exist. Possible values '
                             'are: {}'.format(self.type, self.module, trigger, [*possible_values.keys()]))

        command = self._command.TRIGGER_INPUT
        header = 128 | command.value
        length = 1
        wdata = bytearray([header, length, possible_values[trigger]])
        self.spi_rack.write_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)
        
    def get_trigger_input(self):
        """Gets the trigger input location
        
        Returns:
            trigger_location (string): the currently set trigger input location
        """
        command = self._command.TRIGGER_INPUT
        wdata = bytearray([command.value, 1, 0xFF, 0xFF, 0xFF])
        rdata = self.spi_rack.read_data(self.module, 0, SAMD51_MODE, SAMD51_SPEED, wdata)

        trigger_values = {0:'None', 1:'Controller', 2:'D5b'}
        return trigger_values[rdata[-1]]

    def get_sample_time(self, ADC):
        """Gives the sample rate of the given ADC

        Gives the sample rate in seconds of the ADC. This corresponds to the values in the 
        filter table. These values can be used for plotting or a FFT calculation.
        
        Args:
            ADC (int:0-1): ADC of which to get the sample time
        
        Returns:
            (float): the sample rate in seconds
        """
        if ADC not in range(2):
            raise ValueError('{} module {}: ADC {} does not exist.'.format(self.type, self.module, ADC))

        filter_rate = self.get_filter_rate(ADC)
        filter_type = self.get_filter_type(ADC)

        return self.sample_time[filter_type][filter_rate]


class B2b_Command(Enum):
    CLOCK_SOURCE = 0
    TRIGGER_INPUT = 1
    TRIGGER_HOLDOFF = 2
    TRIGGER_AMOUNT = 3
    GET_FW_VERSION = 4
    GET_MODULE_NAME = 5
    SOFTWARE_TRIGGER = 6
    
    ADC_FILTER_RATE = 7
    ADC_FILTER_TYPE = 8
    ADC_ENABLE = 9
    ADC_SAMPLE_AMOUNT = 10
    ADC_CALIBRATE = 11
    ADC_CONNECTION = 12
    ADC_LOCATION = 13
    
    STATUS_CMD = 14
    CANCEL_CMD = 15
    
    GET_DATA = 16
    READ_LOC = 17
    DATA_LOC = 18

sinc3_sample_time = [
    12e-6,
    24e-6,
    48e-6,
    60e-6,
    96e-6,
    120e-6,
    192e-6,
    300e-6,
    600e-6,
    1.2e-3,
    3e-3,
    6e-3,
    7.5e-3,
    15e-3,
    30e-3,
    50.02e-3,
    60e-3,
    150e-3,
    180e-3,
    300e-3,
    600e-3
]

sinc5_sample_time = [
    20e-6,
    24e-6,
    32e-6,
    36e-6,
    48e-6,
    56e-6,
    80e-6,
    100e-6,
    200e-6,
    400e-6,
    1e-3,
    2e-3,
    2.516e-3,
    5e-3,
    10e-3,
    16.67e-3,
    20.016e-3,
    50e-3,
    60.02e-3,
    100e-3,
    200e-3
]