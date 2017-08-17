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
AD9106_MODE = 0
# Other
ADF4351_MODE = 0  # Frequency synthesizer
LMK01010_MODE = 0 # Clock distribution/division/delay

# SPI clock = MCK/SCBR = 84Mc/SCBR (range 14..255)
LTC2758_SPEED =  6   # 14Mc (40Mc later)
AD9106_SPEED  =  6   # 14Mc (Can go higher)
MAX5702_SPEED =  6   # 14Mc
MAX521x_SPEED =  6   # 14Mc
LMK01010_SPEED = 6   # 14Mc
ADF4351_SPEED = 21   #  4Mc (slow for test)
AD7175_SPEED  = 21   #  4Mc (slow for test)
MCP320x_SPEED = 84   #  1Mc
BICPINS_SPEED = 84   #  1Mc
