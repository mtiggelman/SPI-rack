from .spi_rack import *
from .chip_mode import *
import math
import numpy as np

class S5i_module(object):
    """S5i module interface class

    This class does the low level interfacing with the S5i RF generator module.
    It requires an SPI Rack object and module number at initialization. A start
    up frequency can be given, otherwise it defaults to 100 MHz.
    The RF frequency can be changed via setRfFrequency, which calculates the
    register values and updates the frequency of the ADF4351.
    Attributes:
        rfFrequency: the current set RF output frequency
    """

    def __init__(self, spi_rack, module, frequency=100e6, enable_output=1, output_level=1.0):
    #def __init__(self, module, frequency=100e6):
        """Inits S5i module class

        The S5i module needs an SPI_rack class for communication. If no frequency
        is given at initialization, the output will be set to 100 MHz with a
        stepsize of 1 MHz
        Args:
            spi_rack: SPI_rack class object via which the communication runs
            module: module number set on the hardware
            frequency: RF frequency at startup (in Hz), default 100 MHz
            output_level: RF output level, value between 0-1. Default at full power (1.0)
        Example:
            S5i_1 = S5i_module(SPI_Rack_1, 4)
            S5i_2 = S5i_module(SPI_rack_1, 2, frequency=200, output_level=0.3)
        """
        self.spi_rack = spi_rack
        self.module = module

        self.rf_frequency = frequency
        self.stepsize = 1e6
        self.ref_frequency = 10e6
        self.use_external = 0
        self.output_status = enable_output

        self.set_output_power(output_level)

        # These are the 6 registers present in the ADF4351
        self.registers = 6*[0]
        # In REG3: set ABP=1 (3 ns, INT-N) and CHARGE CANCEL=1
        self.registers[3] = (1<<22) | (1<<21) | 3
        # In REG5: set LD PIN MODE to 1 -> digital lock detect
        self.registers[5] = (1<<22) | (3<<19) | 5

        self.set_frequency(frequency)

    def write_registers(self):
        """Writes data via the SPI Rack class to the SPI Rack

        Writes the current register settings to the ADF4351 in reversed order
        of storage: REG5 to REG0. This is required according to datasheet. The
        output is only updated when REG0 is written to
        """
        for reg in reversed(self.registers):
            b1 = (reg>>24)&0xFF
            b2 = (reg>>16)&0xFF
            b3 = (reg>>8)&0xFF
            b4 = reg&0xFF
            data = bytearray([b1, b2, b3, b4])
            # Write to ADF at SPI address 0
            self.spi_rack.write_data(self.module, 0, ADF4351_MODE, ADF4351_SPEED, data)

    def set_output_power(self, level):
        """Sets the source output power

        Sets the output power of the unit. Can be varied over ~30 dB.
        Args:
            level: value between 0 and 1 (float:0-1)
        """
        if level < 0 or level > 1:
            raise ValueError('Level {} not allowed. Has to be between 0 and 1'.format(level))

        value = int((2**16-1) * level)
        s_data = bytearray([64|(value>>10), (value>>2)&0xFF, (value&3)<<6])
        self.spi_rack.write_data(self.module, 1, MAX521x_MODE, MAX521x_SPEED, s_data)

    def enable_output_soft(self, enable):
        """Enables/disables the output of the generator IC

        Enables/disables the output of the IC, not the same as the mute input on
        the front of the unit. This has less attenuation and is slower.
        Args:
            enable (bool/int: 0-1): enables/disables RF output
        """
        if enable != 0 :
            enable = 1
        self.registers[4] &= 0xFFFFFFDF
        self.registers[4] |= (enable<<5)
        self.write_registers()
        self.output_status = enable

    # Does not do anythin yet
    def use_external_reference(self, use_external):
        #TODO: set bit on backplane to toggle between the two physically
        if use_external == 1:
            self.use_external = 1
            self.ref_frequency = self.spi_rack.ref_frequency
        else:
            self.use_external = 0
            self.ref_frequency = 10e6

    def set_stepsize(self, stepsize):
        """Sets the stepsize to be used in set_frequency()

        Sets the stepsize with which the frequency will be set. Usefull parameters for
        doing sweeps.
        Args:
            stepsize: the stepsize in Hz, must be integer division of reference frequency
        """
        R = self.ref_frequency / stepsize
        if self.ref_frequency % stepsize == 0 and R < 1024:
            self.stepsize = stepsize
        else:
            raise ValueError('"stepsize" value {} not allowed. Must be integer division of reference frequency below 1024'.format(stepsize))

    def set_frequency(self, frequency):
        """Sets the frequency

        Sets the frequency with the grid set by set_stepsize. Will calculate the correct
        register values and raises ValueErrors if the frequency is not possible. Either
        by limitations in the stepsize or when it exceeds the chip requirements.
        Args:
            frequency: wanted output frequency (Hz)
        """
        if frequency > 4.4e9 or frequency < 40e6:
            raise ValueError('Frequency {} not possible. Allowed frequencies: {}<f<{}'.format(frequency, 40e6, 4.4e9))

        #Calculate VCO output divider:
        div = 0
        for n in range(0,7):
            VCO = 2**n * frequency
            if VCO >= 2.2e9 and VCO <= 4.4e9:
                div = n
                break

        #Prescaler: 0 (4/5) if < 3.6 GHz, 1 (8/9) if >= 3.6 GHz
        #Nmin changes with prescaler:
        if frequency >= 3.6e9:
            prescaler = 1
            Nmin = 75
        else:
            prescaler = 0
            Nmin = 23
        #Get R from stepsize and reference frequency
        R = int(self.ref_frequency / self.stepsize)

        if frequency % self.stepsize != 0.0:
            raise ValueError('Frequency must be integer multiple of stepsize: {}'.format(self.stepsize))
        #Calculate INT value
        INT = int(frequency/self.stepsize)
        if INT < Nmin or INT > 65535:
            fmin = max(Nmin * self.stepsize, 40e6)
            fmax = min(self.stepsize*65535, 4.4e9)
            raise ValueError('Frequency {} not possible with stepsize {}. Allowed frequencies: {}<f<{}'.format(frequency, self.stepsize, fmin, fmax))

        #Check that band select is smaller than 10 kHz, otherwise divide
        #until it is
        fpfd = self.ref_frequency/R
        band_sel = 1
        if fpfd > 10e3:
            band_sel = int(math.ceil(fpfd/10e3))
        if band_sel > 255:
            band_sel = 255

        self.rf_frequency = frequency
        # In REG4: Set calculated divider and band select, enable RF out at max power
        self.registers[4] = (div<<20) | (band_sel<<12) | (self.output_status<<5) | (3<<3) | 4
        # In REG2: Set calculated R value, enable double buffer, LDF=INT-N, LDP=6ns, PD_POL = Positive
        self.registers[2] = (R<<14) | (1<<13) | (7<<9) | (1<<8) | (1<<7) | (1<<6) | 2
        # In REG1: Set prescaler value
        self.registers[1] = (prescaler <<27) | (1<<15) | (2<<3) | 1
        # In REG0: Set calculated INT value
        self.registers[0] = (INT<<15)

        self.write_registers()

    def set_frequency_optimally(self, frequency):
        """Calculates and sets the RF output to given frequency

        Calculates the registers for the given RF frequency, optimized for the
        smalles value for the multiplier to minimize the (phase) noise. If the wanted
        frequency is not possible, it will print a warning and set the frequency to
        the closest possible. Writes the settings to the module after calculation
        Args:
            frequency: the wanted output frequency in Hz
        """

        if frequency > 4.4e9 or frequency < 40e6:
            raise ValueError('Frequency {} not possible. Allowed frequencies: {}<f<{}'.format(frequency, 40e6, 4.4e9))

        #Get the backplane reference frequency
        fref = float(self.spi_rack.ref_frequency)

        #Calculate VCO output divider:
        div = 0
        for n in range(0,7):
            VCO = 2**n * frequency
            if VCO >= 2.2e9 and VCO <= 4.4e9:
                div = n
                break

        #Prescaler: 0 (4/5) if < 3.6 GHz, 1 (8/9) if >= 3.6 GHz
        #Nmin changes with prescaler:
        if frequency >= 3.6e9:
            prescaler = 1
            Nmin = 75
        else:
            prescaler = 0
            Nmin = 23

        #Find INT/R relation with minimum size for INT to keep noise as low
        #as possible. Find closest possible frequency if not possible and warn user
        Nmax = int(1023 * frequency / fref)
        n = np.arange(Nmin, Nmax)
        R_t = n*fref/frequency
        R_t_r = np.around(R_t)
        index = np.argmin(np.abs(R_t - R_t_r))
        R = int(R_t_r[index])
        INT = n[index]
        actual_frequency = INT * fref/R
        if actual_frequency != frequency:
            print("Warning! Frequency " + str(frequency) + " not possible, set to closest frequency: " + str(actual_frequency))

        self.rf_frequency = actual_frequency
        #Check that band select is smaller than 10 kHz, otherwise divide
        #until it is
        fpfd = fref/R
        band_sel = 1
        if fpfd > 10e3:
            band_sel = int(math.ceil(fpfd/10e3))
        if band_sel > 255:
            band_sel = 255
        # In REG4: Set calculated divider and band select, enable RF out at max power
        self.registers[4] = (div<<20) | (band_sel<<12) | (self.output_status<<5) | (3<<3) | 4
        # In REG2: Set calculated R value, enable double buffer, LDF=INT-N, LDP=6ns, PD_POL = Positive
        self.registers[2] = (R<<14) | (1<<13) | (7<<9) | (1<<8) | (1<<7) | (1<<6) | 2
        # In REG1: Set prescaler value
        self.registers[1] = (prescaler <<27) | (2<<3) | 1
        # In REG0: Set calculated INT value
        self.registers[0] = (INT<<15)

        self.write_registers()
