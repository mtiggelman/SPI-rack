from .spi_rack import SPI_rack
from .chip_mode import ADF4351_MODE, ADF4351_SPEED, MAX521x_MODE, MAX521x_SPEED, BICPINS_SPEED
import numpy as np

class S5i_module(object):
    """S5i module interface class

    This class does the low level interfacing with the S5i RF generator module.
    It requires an SPI Rack object and module number at initialization. A start
    up frequency can be given, otherwise it defaults to 100 MHz.
    The RF frequency can be changed via set_frequency, which calculates the
    register values and updates the frequency of the ADF4351.

    Attributes:
        rf_frequency (float): the current set RF output frequency
        stepsize (float): the current stepsize
        output_status (bool/int: 0-1): output enabled/disabled by software
    """

    def __init__(self, spi_rack, module, frequency=100e6, enable_output=1, output_level=0.0):
        """Inits S5i module class

        The S5i module needs an SPI_rack class for communication. If no frequency
        is given at initialization, the output will be set to 100 MHz with a
        stepsize of 1 MHz

        Args:
            spi_rack: SPI_rack class object via which the communication runs
            module: module number set on the hardware
            frequency: RF frequency at startup (in Hz), default 100 MHz
            output_level: RF output level, value between -14 to 20. Default at 0 dBm

        Example:
            S5i_1 = S5i_module(SPI_Rack_1, 4)
            S5i_2 = S5i_module(SPI_rack_1, 2, frequency=200e6, output_level=0.3)
        """
        self.spi_rack = spi_rack
        self.module = module

        self.rf_frequency = frequency
        self.stepsize = 1e6
        self.set_reference('internal')
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
            level: value between -20 and 14 (dBm))
        """
        if level < -20 or level > 14:
            raise ValueError('Level {} not allowed. Has to be between -20 and 14 (dBm)'.format(level))

        value = int(1927.5*level + 38550)
        s_data = bytearray([64|(value>>10), (value>>2)&0xFF, (value&3)<<6])
        self.spi_rack.write_data(self.module, 1, MAX521x_MODE, MAX521x_SPEED, s_data)

    def enable_output_soft(self, enable):
        """Enables/disables the output of the generator IC

        Enables/disables the output of the IC, not the same as the mute input on
        the front of the unit. This has less attenuation and is slower.
        Args:
            enable (bool/int: 0-1): enables/disables RF output
        """
        if enable != 0:
            enable = 1
        self.registers[4] &= 0xFFFFFFDF
        self.registers[4] |= (enable<<5)
        self.write_registers()
        self.output_status = enable

    def set_reference(self, reference):
        """
            DO NOT USE EXTERNAL REFERENCE!
        """
        possible_values = {'internal':0, 'external':1}
        if reference not in possible_values:
            raise ValueError('Value {} does not exist. Possible values are: {}'.format(reference, possible_values))

        if reference == 'internal':
            self.spi_rack.write_data(self.module, 5, 0, BICPINS_SPEED, bytearray([1<<3]))
        else:
            self.spi_rack.write_data(self.module, 5, 0, BICPINS_SPEED, bytearray([1<<2]))

        self.reference = reference

    def set_stepsize(self, stepsize):
        """Sets the stepsize to be used in set_frequency()

        Sets the stepsize with which the frequency will be set. Usefull parameters for
        doing sweeps.
        Args:
            stepsize: the stepsize in Hz, must be integer division of reference frequency
        """

        if self.reference == 'internal':
            local_ref = 10e6
        else:
            local_ref = self.spi_rack.ref_frequency

        R = local_ref / stepsize
        if R.is_integer() and R < 1024:
            self.stepsize = stepsize
        else:
            raise ValueError('"stepsize" value {} not allowed. Must be integer division of reference frequency below 1024'.format(stepsize))

    def lock_detect(self):
        """Returns if there is a lock detected

        Return True if module managed to lock to reference signal, otherwise returns False

        Returns:
            True/False depending if lock detected (bool)
        """
        data = self.spi_rack.read_data(self.module, 4, 0, BICPINS_SPEED, bytearray([0]))
        return data[0]&0x01

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

        if self.reference == 'internal':
            local_ref = 10e6
        else:
            local_ref = self.spi_rack.ref_frequency

        #Calculate VCO output divider:
        div = 0
        for n in range(0,7):
            VCO = 2**n * frequency
            if VCO >= 2.2e9 and VCO <= 4.4e9:
                div = n
                break

        #Prescaler: 0 (4/5) if < 3.6 GHz, 1 (8/9) if >= 3.6 GHz
        #Nmin changes with prescaler:
        if frequency >= 1.0e9:
            prescaler = 1
            Nmin = 75
        else:
            prescaler = 0
            Nmin = 23
        #Get R from stepsize and reference frequency
        R = local_ref / self.stepsize

        if not R.is_integer():
            raise ValueError('Frequency must be integer multiple of stepsize: {}'.format(self.stepsize))
        #Calculate INT value
        INT = int(frequency/self.stepsize)
        if INT < Nmin or INT > 65535:
            fmin = max(Nmin * self.stepsize, 40e6)
            fmax = min(self.stepsize*65535, 4.4e9)
            raise ValueError('Frequency {} not possible with stepsize {}. Allowed frequencies: {}<f<{}'.format(frequency, self.stepsize, fmin, fmax))

        band_sel = 255

        self.rf_frequency = frequency
        # In REG4: Set calculated divider and band select, enable RF out at max power
        self.registers[4] = (div<<20) | (band_sel<<12) | (self.output_status<<5) | (3<<3) | 4
        # In REG2: Set calculated R value, enable double buffer, LDF=INT-N, LDP=6ns, PD_POL = Positive
        self.registers[2] = (int(R)<<14) | (1<<13) | (7<<9) | (1<<8) | (1<<7) | (1<<6) | 2
        # In REG1: Set prescaler value
        self.registers[1] = (prescaler <<27) | (1<<15) | (2<<3) | 1
        # In REG0: Set calculated INT value
        self.registers[0] = (INT<<15)

        self.write_registers()

    def get_optimal_stepsize(self, frequency):
        """Calculates and the optimal stepsize for given frequency

        Calculates the stepsize that minimises the phase noise for a given
        frequency.

        Args:
            frequency: the wanted output frequency in Hz
        Returns:
            R: the optimal stepsize
        """
        if frequency > 4.4e9 or frequency < 40e6:
            raise ValueError('Frequency {} not possible. Allowed frequencies: {}<f<{}'.format(frequency, 40e6, 4.4e9))

        #Get the backplane reference frequency
        if self.reference == 'internal':
            local_ref = 10e6
        else:
            local_ref = self.spi_rack.ref_frequency

        #Prescaler: 0 (4/5) if < 3.6 GHz, 1 (8/9) if >= 3.6 GHz
        #Nmin changes with prescaler:
        if frequency >= 1.0e9:
            Nmin = 75
        else:
            Nmin = 23

        #Find INT/R relation with minimum size for INT to keep noise as low
        #as possible.
        Nmax = int(1023 * frequency / local_ref)
        n = np.arange(Nmin, Nmax)
        R_t = n*local_ref/frequency
        R_t_r = np.around(R_t)
        index = np.argmin(np.abs(R_t - R_t_r))
        R = int(R_t_r[index])

        return local_ref/R
