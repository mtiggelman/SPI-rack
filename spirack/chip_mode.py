"""SPI modes for all used chips

Lists all the used chips so far with the corresponding SPI mode. Necessary for
setting the chip select in the SPI Rack
"""
# ADC
AD7175_MODE = 3
MCP320x_MODE = 0
# DAC
LTC2758_MODE = 0
MAX521x_MODE = 1
MAX5702_MODE = 1
# Other
ADF4351_MODE = 0  # Frequency synthesizer
