# Support for firmware-embedded calibration and filament presets using
# SQLite database
#
# Copyright (C) 2023  Florian-Patrice Nagel <flopana77@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

# Printer hardware keys
KEY_EXTRUDER_NAME  = "ex_name"
KEY_FEED_LENGTH  = "feed_length"
KEY_HOTEND_NAME  = "he_name"
KEY_NOZZLE_TYPE  = "noz_type"


# Filament properties keys
KEY_FILAMENT_TYPE  = "f_type"
KEY_FILAMENT_BRAND  = "f_brand"
KEY_FILAMENT_NAME  = "f_name"
KEY_FILAMENT_COLOR  = "f_color"
KEY_FILAMENT_DIAMETER  = "f_diameter"
KEY_FILAMENT_MAX_MANU_TEMP  = "f_max_manu_temp"
KEY_FILAMENT_MIN_MANU_TEMP  = "f_min_manu_temp"

# Filament tuning value keys
# Temperatures
KEY_CHAMBER_TEMP = ""
KEY_STANDBY_NOZZLE_TEMP = ""
KEY_FIRST_LAYER_NOZZLE_TEMP = ""
KEY_NOZZLE_TEMP = ""
KEY_FIRST_LAYER_BED_TEMP = ""
KEY_BED_TEMP = ""
# Flow related
KEY_MAX_VOLUMETRIC_FLOW = ""
KEY_FLOW_RATE = ""
KEY_PRESSURE_ADVANCE = ""
# Cooling
KEY_NO_COOL_LAYER = ""
KEY_MIN_FAN_SPEED_TRESHOLD = ""
KEY_MIN_FAN_SPEED_TIME = ""
KEY_MAX_FAN_SPEED_TRESHOLD = ""
KEY_MAX_FAN_SPEED_TIME = ""          # Min. layer time, slow print down, if set.
KEY_AUX_FAN_SPEED = ""
# Retraction
KEY_RET_LENGTH = ""
KEY_ZHOP_HEIGHT = ""
KEY_ZHOP_TYPE = ""
KEY_RET_SPEED = ""
KEY_UNRET_SPEED = ""
KEY_RET_EXTRA_LENGTH = ""
KEY_WIPE_DIST = ""
KEY_WIPE_SPEED = ""
KEY_RET_BEFORE_WIPE = ""


#class Filament:
    ################################################################# Class init
#    def __init__(self, config):
        # Get References

        # Register new commands



# Functions needed:
# 1) Chamber, nozzle and bed override function
# 2) Flow rate, pressure advance and retraction setting function
# 3) Layer time calculator to slow prints down for layer time
# 4) Fan manipulation function to enforce no cooling, min and max fan dependent
#    on layertime.
#
# Tests to implement
