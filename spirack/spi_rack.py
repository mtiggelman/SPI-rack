from sys import version_info
import threading
import serial
from .chip_mode import MCP320x_MODE, MCP320x_SPEED, ADT7301_SPEED, ADT7301_MODE

class NoLock(object):
    """ Dummy lock object """
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

class SPI_rack(serial.Serial):
    """SPI rack interface class

    The SPI rack class is used to interface with the SPI rack controller unit.
    It implements the protocol used to read and write data and set an active
    module. Use the writeData/readData functions instead of the read/write
    functions of the serial library.

    An instance of SPI rack needs to be passed to every module.

    Attributes:
        active_module: keeps track of which module is currently active
        active_chip: keeps track of which chip in a module is currently active
        active_speed: keeps track of the current SPI speed the controller is set to
        ref_frequency: the current reference frequency (in Hz)
    """

    def __init__(self, port, baud, timeout, use_locks=True):
        """Inits SPI_rack class

        Args:
            port: serial port used by SPI rack controller unit (string)
            baud: baud rate value (int)
            timeout: data receive timout in seconds (float)
            refFrequency: backplane reference frequency in Hz (int)

        Raises:
            ValueError: if parameters (baud rate) are out of range
            SerialException: in case serial device cannot be found or configured

        Example:
            SPI_Rack_1 = SPI_rack("COM1", 1000000, 1)
        """
        try:
            super(SPI_rack, self).__init__(port, baud, timeout=timeout)
        except ValueError:
            print("Timout value out of bound.")
        except serial.SerialException:
            print("Cannot open serial port: " + port)

        self.active_module = None
        self.active_chip = None
        self.active_speed = None
        self.ref_frequency = None

        if use_locks:
            # create a lock for threading
            self._tlock = threading.Lock()
        else:
            self._tlock = NoLock()

    def set_ref_frequency(self, frequency):
        """Set the reference frequency present on the backplane (Hz)

        The reference frequency is shared between all modules. This info
        can be used by other modules for calculation, for example the
        s5i RF generator module needs to know the frequency.

        Args:
            frequency: the reference frequency on the backplane (in Hz)
        """
        self.ref_frequency = frequency

    def _set_active(self, module, chip, SPI_mode, SPI_speed):
        """Set the current module/chip to active on controller unit

        By writing 'c' and then chip/module combination, this chip will
        be set active in the SPI rack controller. This means that all the data
        send after this will go to that chip.

        Args:
            module: module number to set active (int)
            chip: chip in module to set active (int)
            SPI_mode: SPI mode of the chip to be activated (int)
            SPI_speed: SPI clock speed of the chip to be activated (int)
        """

        s_data = bytearray([ord('c'), (chip<<4) | module, SPI_mode, SPI_speed])
        self.write(s_data)

        self.active_module = module
        self.active_chip   = chip
        self.active_speed  = SPI_speed

    def write_data(self, module, chip, SPI_mode, SPI_speed, data):
        """Write data to selected module/chip combination

        Args:
            module   : number of the module to send data to (int)
            chip     : chip in module to send data to (int)
            SPI_mode : SPI mode of the chip to be activated (int)
            SPI_speed: SPI clock speed of the chip to be activated (int)
            data     : array of data to be send (bytearray)
        """

        with self._tlock:
            if(self.active_module != module or self.active_chip != chip or self.active_speed != SPI_speed):
                self._set_active(module, chip, SPI_mode, SPI_speed)

            s_data = bytearray([ord('w')]) + data

            self.write(s_data)

    def read_data(self, module, chip, SPI_mode, SPI_speed, data):
        """Read data from selected module/chip combination

        Args:
            module: number of the module to send data to (int)
            chip: chip in module to send data to (int)
            SPI_mode: SPI mode of the chip to be activated (int)
            data: data to be send to chip for reading (bytearray)

        Returns:
            Bytes received from module/chip (int list)
        """
        with self._tlock:
            if self.active_module != module or self.active_chip != chip or self.active_speed != SPI_speed:
                self._set_active(module, chip, SPI_mode, SPI_speed)

            read_length = len(data)
            data = bytearray([ord('r')]) + data
            self.write(data)
            r_data = self.read(read_length)

        if len(r_data) < read_length:
            print("Received less bytes than expected")

        if version_info[0] < 3:
            return [ord(c) for c in r_data]
        else:
            return r_data

    def get_temperature(self):
        """ Returns the temperature in the C1b module

        Reads the temperature from the internal C1b temperature sensor. Does not
        work for the C1. Accuracy is +- 0.5 degrees in 0-70 degree range

        Returns:
            Temperature (float) in Celcius
        """
        s_data = bytearray([0, 0])
        r_data = self.read_data(0, 1, ADT7301_MODE, ADT7301_SPEED, s_data)
        t_data = (r_data[0]<<8) | r_data[1]

        # Check sign bit for negative value
        if (t_data & 0x2000) == 0x2000:
            return (t_data - 16384)/32

        return t_data/32

    def get_battery(self):
        """Returns battery voltages

        Calculates the battery voltages from the ADC channel values. Currently only
        works for the C1b/C2.

        Returns:
            Voltages (float): [VbatPlus, VbatMin]
        """
        Vbatplus = 2.171*3.3*self.read_adc(1)/4096.0
        Vbatmin = -2.148*3.3*self.read_adc(0)/4096.0
        return [Vbatplus, Vbatmin]

    def read_adc(self, channel):
        """Reads the ADC for battery voltage

        Reads the given ADC channel. These channels are connected to the raw
        of battery. Output needs to calculated due to voltage divider. Function
        used internally.

        Args:
            channel (int: 0-1): the ADC channel to be read
        Returns:
            12-bit ADC data (int)
        """
        s_data = bytearray([1, 160|(channel<<6), 0])
        r_data = self.read_data(0, 0, MCP320x_MODE, MCP320x_SPEED, s_data)

        return (r_data[1] & 0xf)<<8 | r_data[2]

    def unlock(self):
        """Unlocks SPI communication

        After power-up of the Arduino DUE, SPI write communication is
        blocked as a safety precaution when working with DAC Modules.
        By preventing SPI write actions to be performed, the current DAC
        state is preserved and can be read back by the user.

        Args:
            none
        Returns:
            none
        """
        with self._tlock:
            s_data = bytearray([ord('u')])
            self.write(s_data)


    def lock(self):
        """Locks SPI communication

        Prevent SPI write actions. See 'unlock'.

        Args:
            none
        Returns:
            none
        """

        with self._tlock:
            s_data = bytearray([ord('l')])
            self.write(s_data)
