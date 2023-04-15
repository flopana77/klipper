# Support for Marlin/Smoothie/Reprap style firmware retraction via G10/G11
#
# Copyright (C) 2019  Len Trigg <lenbok@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

class FirmwareRetraction:
    def __init__(self, config):
        # Get a reference to the printer object from the config
        self.printer = config.get_printer()
        
        # Initialize various retraction-related parameters from the config
        self.retract_length = config.getfloat('retract_length', 0., minval=0.)
        self.retract_speed = config.getfloat('retract_speed', 20., minval=1)
        self.unretract_extra_length = config.getfloat('unretract_extra_length', 0., minval=0.)
        self.unretract_speed = config.getfloat('unretract_speed', 10., minval=1)
        
        ############################################################################################################### Added z_hop with 2mm minimum...change later to 0.
        self.z_hop = config.getfloat('z_hop', 0., minval=0.)
        
        # Initialize unretract length and retracted state
        self.unretract_length = (self.retract_length + self.unretract_extra_length)
        self.is_retracted = False
        
        # Get a reference to the G-code object from the printer object
        self.gcode = self.printer.lookup_object('gcode')
        
        # Register new G-code commands for setting/retrieving retraction parameters
        self.gcode.register_command('SET_RETRACTION', self.cmd_SET_RETRACTION, desc=self.cmd_SET_RETRACTION_help)
        self.gcode.register_command('GET_RETRACTION', self.cmd_GET_RETRACTION, desc=self.cmd_GET_RETRACTION_help)
        
        # Register new G-code commands for firmware retraction/unretraction
        self.gcode.register_command('G10', self.cmd_G10)
        self.gcode.register_command('G11', self.cmd_G11)
    
    # Helper method to return the current retraction parameters
    def get_status(self, eventtime):
        return {
            "retract_length": self.retract_length,
            "retract_speed": self.retract_speed,
            "unretract_extra_length": self.unretract_extra_length,
            "unretract_speed": self.unretract_speed,
            
            ################################################################################################################ Added back z_hop
            "z_hop": self.z_hop,
            ################################################################################################################ Add unretract_length and is_retracted to status output
            "retract_length": self.unretract_length,
            "retract_state": self.is_retracted
        }
    
    # Help message for SET_RETRACTION command, obtained by issuing HELP command
    cmd_SET_RETRACTION_help = ("Set firmware retraction parameters")
    
    # Command to set the firmware retraction parameters
    def cmd_SET_RETRACTION(self, gcmd):
        self.retract_length = gcmd.get_float('RETRACT_LENGTH', self.retract_length, minval=0.)
        self.retract_speed = gcmd.get_float('RETRACT_SPEED', self.retract_speed, minval=1)
        self.unretract_extra_length = gcmd.get_float('UNRETRACT_EXTRA_LENGTH', self.unretract_extra_length, minval=0.)
        self.unretract_speed = gcmd.get_float('UNRETRACT_SPEED', self.unretract_speed, minval=1)
        
        ################################################################################################################ Added back z_hop with 2mm minimum CHANGE LATER
        self.z_hop = self.gcode.get_float('Z_HOP', self.z_hop, minval=0.)
        
        self.unretract_length = (self.retract_length + self.unretract_extra_length)
        self.is_retracted = False
    
    # Help message for GET_RETRACTION command
    cmd_GET_RETRACTION_help = ("Report firmware retraction paramters")
    
    # Command to report the current firmware retraction parameters
    def cmd_GET_RETRACTION(self, gcmd):
        gcmd.respond_info("RETRACT_LENGTH=%.5f RETRACT_SPEED=%.5f"
                          "UNRETRACT_EXTRA_LENGTH=%.5f UNRETRACT_SPEED=%.5f"
                          
                          ################################################################################################# Added back z-hop
                          "Z_HOP=%.5f"
                          % (self.retract_length, self.retract_speed,
                             self.unretract_extra_length, self.unretract_speed,
                             ################################################################################################# Added back z-hop
                             self.z_hop))
    
    # Gcode Command G10 to perform firmware retraction
    def cmd_G10(self, gcmd):
        # If the filament isn't already retracted
        if not self.is_retracted:
            # Use the G-code script to save the current state, move the filament, and restore the state
            self.gcode.run_script_from_command(
                "SAVE_GCODE_STATE NAME=_retract_state\n"
                "G91\n"
                "G1 E-%.5f F%d\n"
                
                ################################################################################################# Added back z-hop
                "G1 Z%.5f\n"
                "RESTORE_GCODE_STATE NAME=_retract_state"
                
                ################################################################################################# Added back z-hop
                % (self.retract_length, self.retract_speed*60, self.z_hop))
            
            # Set the flag to indicate that the filament is retracted
            self.is_retracted = True

    # GCode Command G11 to perform filament unretraction
    def cmd_G11(self, gcmd):
        # If the filament is currently retracted
        if self.is_retracted:
            # Use the G-code script to save the current state, move the filament, and restore the state
            self.gcode.run_script_from_command(
                "SAVE_GCODE_STATE NAME=_retract_state\n"
                "G91\n"
                "G1 E%.5f F%d\n"
                
                ################################################################################################# Added back un z-hop
                "G1 Z-%.5f\n"
                "RESTORE_GCODE_STATE NAME=_retract_state"
                
                ################################################################################################# Added back un z-hop
                % (self.unretract_length, self.unretract_speed*60, self.z_hop))
            
            # Set the flag to indicate that the filament is not retracted
            self.is_retracted = False
            
# Function to load the FirmwareRetraction class from the configuration file
def load_config(config):
    return FirmwareRetraction(config)
