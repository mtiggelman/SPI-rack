# SPI Rack
The SPI Rack is a modular electronic instrumentation platform developed by QuTech. It has been developed to perform measurements on nanoelectronic devices, but is not limited to this. Design priority was the minimization of noise and interference signals on the wires connected to the measured device (sample). To learn more about the SPI Rack, use cases and the available modules, browse the [homepage](http://qtwork.tudelft.nl/~mtiggelman/).

This repository contains the Python code to interface with the hardware. All the low level communication is handled by the classes and the user is presented with an easy interface to control the modules. Here is a simple example on how to use the D5a (16 channel 18-bit DAC module) to show how easy it is to get going:

```Python
# Import parts of the SPI Rack library
from spirack import SPI_rack, D5a_module

# Instantiate the controller module
spi = SPI_rack(port="COM4", baud=9600, timeout=1)
# Unlock the controller for communication to happen
spi.unlock()

# Instantiate the D5a module using the controller module
# and the correct module address
D5a = D5a_module(spi, module=2)
# Set the output of DAC 1 to the desired voltage
D5a.set_voltage(0, voltage=2.1)
```
More examples can be found as Jupyter notebooks in [examples](https://github.com/mtiggelman/SPI-rack/tree/master/examples) or at the [website](http://qtwork.tudelft.nl/~mtiggelman/software/examples.html).

## Installation
**Windows 7&8 users:** before connecting the SPI-rack for the first time, install the drivers located
in `drivers.zip`. On 64-bit systems run `SPI-Rack_x64`, on 32-bit systems
run `SPI-Rack_x86`. This is not necessary anymore for Windows 10 systems.

For a basic install use: `pip install spirack`. For more details see the website [here](http://qtwork.tudelft.nl/~mtiggelman/software/setup.html).

## Qcodes
Qcodes wrappers for certain modules are available from https://github.com/QCoDeS/Qcodes

## License
See [License](https://github.com/mtiggelman/SPI-rack/blob/master/LICENSE).
