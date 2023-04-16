# Support for Marlin/Smoothie/Reprap style firmware retraction via G10/G11
#
# Copyright (C) 2019  Len Trigg <lenbok@gmail.com>
# Copyright (C) 2023  Florian-Patrice Nagel <flopana77@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

class FirmwareRetraction:
    def __init__(self, config):
        # Get a reference to the printer object from the config
        self.printer = printer = config.get_printer()
        
        # Get a reference to the gcode object
        self.gcode = printer.lookup_object('gcode')
        
        # Get a reference to the gcode_move object
        self.gcode_move = printer.lookup_object('gcode_move')
        
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
            
            # Set the flag to indicate that the filament is retracted and activate G1 method with z-hop compensation
            self.is_retracted = True
            logging.debug("cmd_G10: Calling self.unregister_G1 method")
            self.unregister_G1()

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
            
            # Set the flag to indicate that the filament is not retracted and activate original G1 method 
            self.is_retracted = False
            logging.debug("cmd_G11: Calling self.re_register_G1 method")
            self.re_register_G1()
    
    ##########################################################################################  Registrer new G1 command handler
    def unregister_G1(self):
        # Unregister the original G1 method from the G1 command and
        # store the associated method in prev_cmd
        prev_cmd = self.gcode.register_command("G1", None)
        logging.debug("unregister_G1: Previous G1 command registred")

        # Now, register the original G1 method with the new G1.20140114 command,
        # and set its description to indicate it's a renamed built-in command
        pdesc = "Renamed builtin of '%s'" % ("G1")
        self.gcode.register_command('G1.1', prev_cmd, desc=pdesc)
        logging.debug("unregister_G1: Original G1 method re-registred to G1.20140114")
        
        # Register the G0 and the G1 commands with the z-hop G1 method
        self.gcode.register_command('G0', self.cmd_G1_zhop)
        logging.debug("unregister_G1: New G1 method registred to G0")
        
        cmd_desc = "G1 command that accounts for z hop when retracted"
        self.gcode.register_command('G1', self.cmd_G1_zhop, desc=cmd_desc)
        logging.debug("unregister_G1: New G1 method registred to G1")
    
    ##########################################################################################  Re-registrer old G1 command handler
    def re_register_G1(self):
        # Unregister the original G1 method from the G1.20140114 command and
        # store the associated method in prev_cmd
        prev_cmd = self.gcode.register_command("G1.1", None)
        logging.debug("re_register_G1: Previous G1 command registred")

        # Now, register the original G1 method with the old G1 command,
        # and set empty description
        self.gcode.register_command("G1", prev_cmd, desc=None)
        logging.debug("re_register_G1: Register original G1 method to G1 command")
        
        # Re-register the G0 command with the original G1 method
        self.gcode.register_command('G0', self.gcode_move.cmd_G1)
        logging.debug("re_register_G1: Register original G1 method to G0 command")

    
    ######################################################################################### G1 method that accounts for z-hop by altering the z-coordinates
    def cmd_G1_zhop(self,gcmd):
        params = gcmd.get_command_parameters()
        logging.debug("cmd_G1_zhop: Params received")
        
        # Check if there's a Z movement in the command
        if 'Z' in params:
            # Adjust the Z value to account for the Z-hop offset
            params['Z'] = str(float(params['Z']) + self.z_hop)

            # Reconstruct the G1 command with adjusted parameters
            new_g1_command = "G1.1"
            for key, value in params.items():
                new_g1_command += f" {key}{value}"

            # Run the G1.20140114 command with the adjusted parameters
            self.gcode.run_script_from_command(new_g1_command)
    
# Function to load the FirmwareRetraction class from the configuration file
def load_config(config):
    return FirmwareRetraction(config)
