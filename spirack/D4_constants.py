"""Constants for AD7175-2

Contains necessary constants in use in the D4 module. All the names of the
registers are identical to datasheet names.
"""

# ADC register values
STATUS_REG = 0x00
MODE_REG = 0x01
IFMODE = 0x02
DATA_REG = 0x04
CH1_REG = 0x10
CH2_REG = 0x11
CH3_REG = 0x12
CH4_REG = 0x13
CONFIG_REG = 0x20
FILTER_REG = 0x28

# ADC register positions
REF_EN = 15
SING_CYC = 13
MODE = 4

DOUT_RESET = 8
IOSTRENGTH = 11

CH_EN = 15
SETUP_SEL = 12
AINPOS = 5
AINNEG = 0

BI_UNIPOLAR = 12
REFBUF0P = 11
REFBUF0M = 10
AINBUF0P = 9
AINBUF0M = 8
REF_SEL = 4

ENHFILTEN = 11
ENHFILT = 8
ORDER0 = 5
ODR = 0

# ADC register values
AIN0 = 0
AIN1 = 1
AIN2 = 2
AIN3 = 3
AIN4 = 4
REFP = 21
REFN = 22
