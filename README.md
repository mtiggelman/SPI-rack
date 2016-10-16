### Project structure

- `drivers`: USB communication drivers for Windows
- `<module>`
  - `<module>_module.py`: Low-level code for communicating with the module hardware.
  - `<module>.py`: QCoDeS instrument wrapper
- `spi_rack.py`: This class is used by the modules to communicate with the SPI rack
