"""SPI modes and speeds for all used chips

Lists all the used chips so far with the corresponding SPI mode and speeds.
Necessary for setting the chip select in the SPI Rack

The speeds are set by a divisor: 84MHz/value (range 14..255), these are the
numbers in the list below. Zero is a special value which sets the SPI speed to
1kHz (software SPI)
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
BICPINS_MODE = 0
ADT7301_MODE = 0 # C1b temperature sensor
CRYOMUX_MODE = 0 # cryomux shift register
SAMD51_MODE = 0 # SAMD51G19A microcontroller

# SPI clock = MCK/SCBR = 84MHz/SCBR (range 14..255)
LTC2758_SPEED = 6       # 14MHz (40MHz later)
LTC2758_RD_SPEED = 8    # 10.5MHz
AD9106_SPEED = 6        # 14MHz (Can go higher)
SAMD51_SPEED = 6        # 14MHz (assuming uc running at 100+ MHz core speed)
MAX5702_SPEED = 6       # 14MHz
MAX521x_SPEED = 6       # 14MHz
LMK01010_SPEED = 6      # 14MHz
ADF4351_SPEED = 21      #  4MHz (slow for test)
AD7175_SPEED = 21       #  4MHz (slow for test)
MCP320x_SPEED = 84      #  1MHz
BICPINS_SPEED = 84      #  1MHz
ADT7301_SPEED = 84      #  1MHz
CRYOMUX_SPEED = 0       #  1kHz
