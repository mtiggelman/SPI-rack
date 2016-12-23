from spi_rack import *
from chip_mode import *
import math

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

    def __init__(self, spi_rack, module, frequency=100):
        """Inits S5i module class

        The S5i module needs an SPI_rack class for communication. If no frequency
        is given at initialization, the output will be set to 100 MHz.

        Args:
            spi_rack: SPI_rack class object via which the communication runs
            module: module number set on the hardware
            frequency: RF frequency at startup, default 100 MHz
        Example:
            S5i_1 = S5i_module(SPI_Rack_1, 4)
        """
        self.spi_rack = spi_rack
        self.module = module

        self.rf_frequency = frequency
        self.outputPower = None

        # These are the 6 registers present in the ADF4351
        self.registers = 6*[0]
        # In REG3: set ABP=1 (3 ns, INT-N) and CHARGE CANCEL=1
        self.registers[3] = (1<<22) | (1<<21) | 3
        # In REG5: set LD PIN MODE to 1 -> digital lock detect
        self.registers[5] = (1<<22) | 5

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
            self.spi_rack.write_data(self.module, 0, ADF4351_MODE, data)

    def set_frequency(self, frequency):
        """Calculates and sets the RF output to given frequency

        Calculates the registers for the given RF frequency, optimized for the
        smalles value for the multiplier to minimize the (phase) noise. Writes
        the settings to the module after calculation

        Args:
            frequency: the wanted output frequency in MHz
        """
        ###
        #TODO:  add doubler/divided in algorithm to potentially lower noise
        #       add checks to see if possible to set frequency
        #       add user feedback in case of problems
        ###

        #Get the backplane reference frequency
        fref = float(self.spi_rack.ref_frequency)
        #Calculate VCO output divider:
        div = 0
        for n in range(0,7):
            VCO = 2**n * frequency
            if VCO >= 2200 and VCO <= 4400:
                div = n
                break
        #Prescaler: 0 (4/5) if < 3.6 GHz, 1 (8/9) if >= 3.6 GHz
        #Nmin changes with prescaler:
        if frequency >= 3600.0:
            prescaler = 1
            Nmin = 75
        else:
            prescaler = 0
            Nmin = 23

        #Find INT/R relation with minimum size for INT to keep noise as low
        #as possible
        INT = 0
        R = 0
        for n in range(Nmin, 65536):
            R_t = (n*fref)/(frequency)
            if R_t.is_integer():
                INT = n
                R = int(R_t)
                break

        #Check that band select is smaller than 125 kHz, otherwise divide
        #until it is
        fpfd = fref/R
        band_sel = 1
        if fpfd > 0.125:
            band_sel = int(math.ceil(fpfd/0.125))

        # In REG4: Set calculated divider and band select, enable RF out at max power
        self.registers[4] = (div<<20) | (band_sel<<12) | (1<<5) | (3<<3) | 4
        # In REG2: Set calculated R value, enable double buffer, LDF=INT-N, LDP=6ns, PD_POL = Positive
        self.registers[2] = (R<<14) | (1<<13) | (7<<9) | (1<<8) | (1<<7) | (1<<6) | 2
        # In REG1: Set prescaler value
        self.registers[1] = (prescaler <<27) | 1
        # In REG0: Set calculated INT value
        self.registers[0] = (INT<<15)

        self.write_registers()
