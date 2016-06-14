from qcodes import Instrument, VisaInstrument
from qcodes.utils.validators import Numbers, Ints

from .D5a_module import D5a_module

from functools import partial

class D5a(Instrument):
    def __init__(self, name, spi_rack, module, **kwargs):
        super().__init__(name, **kwargs)

        self.d5a = D5a_module(spi_rack, module)

        print('Creating qcodes instrument')

        for i in range(16):
            self.add_parameter('dac{}'.format(i + 1),
                               label='DAC {} (V)'.format(i + 1),
                               get_cmd=partial(self._get_dac, i),
                               #set_cmd=partial(self._set_dac, i),
                               set_cmd=self.test,
                               units='V',
                               delay=0.1)

    def _get_dac(self, dac):
        #return self.d5a.read_value(dac)
        return 0

    def test(self, val):
        print(val)

    def _set_dac(self, dac, value):
        print('Settings DAC {} to {}'.format(dac, value))
        self.d5a.change_value_update(dac, value)