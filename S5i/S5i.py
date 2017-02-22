from qcodes import Instrument
from qcodes.utils.validators import Numbers

from .S5i_module import S5i_module


class S5i(Instrument):
    """
    Qcodes driver for the S5i RF generator SPI-rack module.
    """
    def __init__(self, name, spi_rack, module, **kwargs):
        super().__init__(name, **kwargs)
        self._frequency = 100
        self.s5i = S5i_module(spi_rack, module)

        self.add_parameter('frequency',
                           label='Frequency',
                           get_cmd=self._get_rf_frequency,
                           set_cmd=self._set_rf_frequency,
                           unit='MHz',
                           vals=Numbers())

    def _get_rf_frequency(self):
        return self._frequency

    def _set_rf_frequency(self, frequency):
        self._frequency = frequency
        self.s5i.set_frequency_optimally(frequency)
