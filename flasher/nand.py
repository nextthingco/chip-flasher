# This file contains the threshhold limits for the NAND test for the hwtest that's run on CHIP
# The output of the NAND test has the form:
# Checking bitflips on NAND... [uncorrectable-bit-flips] [max-correctable-bitflips] [std-dev-of-max-correctable-bitflips]
# for example:
# Checking bitflips on NAND... 0 49.9 1.64012

MAX_UNCORRECTABLE_BITFLIPS = 0 
MAX_CORRECTABLE_BITFLIPS = 99
MAX_STD_DEV_CORRECTABLE_BITFLIPS = 10
