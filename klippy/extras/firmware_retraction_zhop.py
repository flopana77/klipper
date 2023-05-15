# Support for Marlin/Smoothie/Reprap style firmware retraction via G10/G11
#
# Copyright (C) 2023  Florian-Patrice Nagel <flopana77@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

class FirmwareRetraction:
    ########################################################################################## Class init
    def __init__(self, config):
        # Get a reference to the printer object from the config after all components are registered
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:ready", self._handle_ready)
        
        # Register Events to clear retraction
        #self.printer.register_event_handler("klippy:ready", self.cmd_CLEAR_RETRACTION)
        
        # Define valid z_hop styles
        self.valid_z_hop_styles = ['standard','ramp', 'helix']
        
        # Initialize various retraction-related parameters from the config
        self.retract_length = config.getfloat('retract_length', 0., minval=0.)
        self.retract_speed = config.getfloat('retract_speed', 20., minval=1)
        self.unretract_extra_length = config.getfloat('unretract_extra_length', 0., minval=0.)
        self.unretract_speed = config.getfloat('unretract_speed', 10., minval=1)
        self.z_hop_height = config.getfloat('z_hop_height', 0., minval=0.)  # Added z_hop_height with 0mm minimum...Standard value is cero to prevent any incompatibility issues on merge
        self.z_hop_style = config.get('z_hop_style', default='standard').strip().lower()    # Added z_hop_style to config, "Linear" or "Helix" for Bambu Lab style zhop. format all lower case and define valid inputs.
        self._check_z_hop_style()
        self.verbose = config.get('verbose', default=False) # Added verbose to config to enable7disable user messages
        
        # Get other values from config
        zconfig = config.getsection('stepper_z')
        self.max_z = zconfig.getfloat('position_max', note_valid=False)
        
        # Initialize number variables
        self.unretract_length = (self.retract_length + self.unretract_extra_length)
        self.currentZ = 0.0             # Current Gcode Z coordinate
        self.z_hop_Z = 0.0              # Gcode Z coordinate of the zhop move
        self.safe_z_hop_height = 0.0    # zhop height applied to prevent out-of-range moves

        # Initialize boolean variables
        self.is_retracted = False
        self.ramp_move = False
    
    # Helper method to return the current retraction parameters
    def get_status(self, eventtime):
        return {
            'retract_length': self.retract_length,
            'retract_speed': self.retract_speed,
            'unretract_extra_length': self.unretract_extra_length,
            'unretract_speed': self.unretract_speed,
            'z_hop_height': self.z_hop_height, # Added back z_hop_height and included z_hop style and safe z_hop height
            'safe_z_hop_height': self.safe_z_hop_height,
            'z_hop_style': self.z_hop_style,
            'unretract_length': self.unretract_length, # Add unretract_length and is_retracted to status output
            'retract_state': self.is_retracted
        }
    
    ########################################################################################## Command to set the firmware retraction parameters
    cmd_SET_RETRACTION_help = ('Set firmware retraction parameters')
    
    def cmd_SET_RETRACTION(self, gcmd):
        # SET_RETRACTION can only be executed when unretracted to prevent error and nozzle crashing
        if not self.is_retracted:
            self.retract_length = gcmd.get_float('RETRACT_LENGTH', self.retract_length, minval=0.)
            self.retract_speed = gcmd.get_float('RETRACT_SPEED', self.retract_speed, minval=1)
            self.unretract_extra_length = gcmd.get_float('UNRETRACT_EXTRA_LENGTH', self.unretract_extra_length, minval=0.)
            self.unretract_speed = gcmd.get_float('UNRETRACT_SPEED', self.unretract_speed, minval=1)
            self.z_hop_height = gcmd.get_float('Z_HOP_HEIGHT', self.z_hop_height, minval=0.)    # Added back z_hop_height with 0mm minimum
            self.z_hop_style = gcmd.get('Z_HOP_STYLE', self.z_hop_style).strip().lower()
            self.unretract_length = (self.retract_length + self.unretract_extra_length)
            self.is_retracted = False
        else:
            gcmd.respond_info('Printer in retract state. SET_RETRACTION can only be executed while unretracted!')

    ########################################################################################## Command to report the current firmware retraction parameters
    cmd_GET_RETRACTION_help = ('Report firmware retraction paramters')
    
    def cmd_GET_RETRACTION(self, gcmd):
        gcmd.respond_info('RETRACT_LENGTH=%.5f RETRACT_SPEED=%.5f '
                          'UNRETRACT_EXTRA_LENGTH=%.5f UNRETRACT_SPEED=%.5f'
                          ' Z_HOP_HEIGHT=%.5f Z_HOP_STYLE=%s '
                          % (self.retract_length, self.retract_speed,
                             self.unretract_extra_length, self.unretract_speed,
                             self.z_hop_height, self.z_hop_style )) # Added back z-hop

    ########################################################################################## Command to report the current firmware retraction parameters
    cmd_CLEAR_RETRACTION_help = ('Clear retraction state without retract move or zhop, if enabled')
    
    def cmd_CLEAR_RETRACTION(self, gcmd):
        if self.is_retracted:
            self._re_register_G1()      # Re-establish regular G1 command. zhop will be reversed on next move with z coordinate
            self.is_retracted = False   # Remove retract flag to enable new retraction move
            if self.verbose: gcmd.respond_info('Retraction cleared. zhop undone on next move.')
        else:
            if self.verbose: gcmd.respond_info('Printer is not retracted. Command ignored!')
            
    ########################################################################################## Gcode Command G10 to perform firmware retraction
    def cmd_G10(self, gcmd):
        # Check homing status
        homing_status = self._get_homing_status()
        # If printer is not homed
        if 'xyz' not in homing_status:
            if self.verbose: gcmd.respond_info('Printer is not homed. Command ignored!')
        # If the filament isn't already retracted
        elif not self.is_retracted:
            # Build the G-Code string to retract
            retract_gcode = (
                "SAVE_GCODE_STATE NAME=_retract_state\n"
                "G91\n"
                "G1 E-{:.5f} F{}\n"
                "G90\n" # Switch back to absolute mode given that the following commands are in absolute mode
            ).format(self.retract_length, int(self.retract_speed * 60))

            # Include move command if z_hop_height greater 0 depending on z_hop_style
            if self.z_hop_height <= 0.0:
                # If z_hop disabled (z_hop_height equal to or less than 0), no move except extruder
                retract_gcode += "RESTORE_GCODE_STATE NAME=_retract_state"
            else:
                # Set safe zhop parameters to prevent out-of-range moves when canceling or finishing print while retracted
                self._set_safe_zhop_params()

                if self.z_hop_style == 'helix':
                    
                    # ADD THE CODE FOR GET NEXT COORDINATE AND CALCULAT HELIX CENTER POINT HERE!!!!!!!
                    
                    retract_gcode += (
                        "G17\n" # Set XY plane for 360 degree arc move (including z move results in a helix)
                        "G2 Z{:.5f} I-1.22 J0\n"
                    ).format(self.z_hop_Z)
                # Standard vertical move with enabled z_hop_height
                elif self.z_hop_style == 'standard':
                    retract_gcode += (
                        "G1 Z{:.5f}\n"
                    ).format(self.z_hop_Z)
                # Ramp move: z_hop performed during first G1 move after retract command
                elif self.z_hop_style == 'ramp':
                    # Set flag to trigger ramp move in the next G1 command
                    self.ramp_move = True
                
                # Restore state in all three cases
                retract_gcode += "RESTORE_GCODE_STATE NAME=_retract_state"
                            
            # Use the G-code script to save the current state, move the filament, and restore the state
            self.gcode.run_script_from_command(retract_gcode)
            # Set the flag to indicate that the filament is retracted and activate G1 method with z-hop compensation
            self.is_retracted = True
            
            # Swap original G1 handlers if z_hop enabled (z_hop_height greater 0)
            if self.z_hop_height > 0.0:
                self._unregister_G1()
        else:
            if self.verbose: gcmd.respond_info('Printer is already in retract state. Command ignored!')

    ########################################################################################## GCode Command G11 to perform filament unretraction
    def cmd_G11(self, gcmd):
        # If the filament is currently retracted
        if self.is_retracted:
            # Restore original G1 handlers if z_hop enabled (z_hop_height greater 0)
            if self.z_hop_height > 0.0:
                self._re_register_G1()

            # Build the G-Code string to unretract
            unretract_gcode = (
                "SAVE_GCODE_STATE NAME=_unretract_state\n"
                "G91\n"
                "G1 E{:.5f} F{}\n"
            ).format(self.unretract_length, int(self.unretract_speed * 60))
            
            # Include move command only if z_hop enabled
            if self.z_hop_height <= 0.0 or self.ramp_move:
                # z_hop disabled or ramp move not executed, no move except extruder
                unretract_gcode += "RESTORE_GCODE_STATE NAME=_unretract_state"
            else:          
                unretract_gcode += (
                    "G1 Z-{:.5f}\n"
                    "RESTORE_GCODE_STATE NAME=_unretract_state"
                ).format(self.safe_z_hop_height)
                       
            # Use the G-code script to save the current state, move the filament, and restore the state
            self.gcode.run_script_from_command(unretract_gcode)
            
            # Set the flag to indicate that the filament is not retracted and activate original G1 method 
            self.is_retracted = False
        else:
            if self.verbose: gcmd.respond_info('Printer is not retracted. Command ignored!')
    
    ######################################################################################### G1 method that accounts for z-hop by altering the z-coordinates. Offsets are not touched to prevent incompatibility issues
    def _G1_zhop(self,gcmd):
        params = gcmd.get_command_parameters()
        
        # Check if ramp flag set
        if self.ramp_move:
            # Reset flag
            self.ramp_move = False
            if not 'Z' in params:
                # If the first move after retract does not have a Z parameter, add parameter equal to z_hop_Z to create ramp move
                params['Z'] = str(self.z_hop_Z)
            else:
                # If the first move after retract does have a Z parameter, simply adjust the Z value to account for the additonal Z-hop offset
                params['Z'] = str(float(params['Z']) + self.safe_z_hop_height)
        elif 'Z' in params:
            # Adjust the Z value to account for the Z-hop offset after retract and ramp move (if applicable)
            params['Z'] = str(float(params['Z']) + self.safe_z_hop_height)

        # Reconstruct the G1 command with adjusted parameters
        new_g1_command = 'G1.20140114'
        for key, value in params.items():
            new_g1_command += f' {key}{value}'

        # Run the G1.20140114 command with the adjusted parameters
        self.gcode.run_script_from_command(new_g1_command)

    ########################################################################################## Register new G1 command handler    
    def _unregister_G1(self):
        self._toggle_gcode_commands('G1.20140114', 'G1', self._G1_zhop, 'G1 command that accounts for z hop when retracted', False)
        self._toggle_gcode_commands('G0.20140114', 'G0', self._G1_zhop, 'G0 command that accounts for z hop when retracted', False)
    
    ########################################################################################## Re-register old G1 command handler
    def _re_register_G1(self):
        self._toggle_gcode_commands('G1', 'G1.20140114', None, 'cmd_G1_help', True)
        self._toggle_gcode_commands('G0', 'G0.20140114', None, 'cmd_G1_help', True)
        
    ########################################################################################## Helper to check that z_hop_style was input and is valid.
    def _check_z_hop_style(self):   
        if self.z_hop_style not in self.valid_z_hop_styles:
            self.z_hop_style = 'standard'
            logging.warning('The provided z_hop_style value is invalid. Using "standard" as default.')
            
    ########################################################################################## Helper to get current gcode position.
    def _get_gcode_zpos(self):        
        # Get current gcode position for z_hop move if enabled
        gcodestatus = self.gcode_move.get_status()
        currentPos = gcodestatus['gcode_position']
        return currentPos[2]

    ########################################################################################## Helper to get current gcode position.
    def _set_safe_zhop_params(self):
        self.currentZ = self._get_gcode_zpos()
        
        # Set safe z_hop height to prevent out-of-range moves. Variable used in zhop-G1 command
        if self.currentZ + self.z_hop_height > self.max_z:
            self.safe_z_hop_height = self.max_z - self.currentZ
        else:
            self.safe_z_hop_height = self.z_hop_height
        
        # Set safe z_hop position to prevent out-of-range moves
        self.z_hop_Z = self.currentZ + self.safe_z_hop_height
    
    ########################################################################################## Helper to get homing status
    def _get_homing_status(self):        
        # Check if Z axis is homed
        curtime = self.printer.get_reactor().monotonic()
        kin_status = self.toolhead.get_kinematics().get_status(curtime)
        return kin_status['homed_axes']
    
    ########################################################################################## Helper to toggle/untoggle command handlers and methods
    def _toggle_gcode_commands(self, new_cmd_name, old_cmd_name, new_cmd_func, new_cmd_desc, toggle_state):
        # Unregister the current command method from the current command handler and
        # store in prev_cmd
        prev_cmd = self.gcode.register_command(old_cmd_name, None)
        pdesc = 'Renamed builtin of "%s"' % old_cmd_name
        if not toggle_state:
            # Register the previous command method with the toggled command handler and
            # set its description to indicate it is a built-in command
            self.gcode.register_command(new_cmd_name, prev_cmd, desc=pdesc)
            # Register the toggled command method with the current command handler
            self.gcode.register_command(old_cmd_name, new_cmd_func, desc=new_cmd_desc)
        else:
            # Unregister the toggled command method from the untoggled command handler
            self.gcode.register_command(new_cmd_name, new_cmd_func)
            # Register the untoggled command method with the untoggled command handler
            self.gcode.register_command(new_cmd_name, prev_cmd, desc=new_cmd_desc)
    
    ########################################################################################## Helper method to register commands and instantiate required objects
    def _handle_ready(self):
        self.gcode = self.printer.lookup_object('gcode')    # Get a reference to the gcode object
        self.gcode_move = self.printer.lookup_object('gcode_move')  # Get a reference to the gcode_move object
        self.toolhead = self.printer.lookup_object('toolhead')  # Get a reference to the toolhead object
        
        # Register new G-code commands for setting/retrieving retraction parameters and clearing retraction
        self.gcode.register_command('SET_RETRACTION', self.cmd_SET_RETRACTION, desc=self.cmd_SET_RETRACTION_help)
        self.gcode.register_command('GET_RETRACTION', self.cmd_GET_RETRACTION, desc=self.cmd_GET_RETRACTION_help)
        self.gcode.register_command('CLEAR_RETRACTION', self.cmd_CLEAR_RETRACTION, desc=self.cmd_CLEAR_RETRACTION_help)
        
        # Register new G-code commands for firmware retraction/unretraction
        self.gcode.register_command('G10', self.cmd_G10)
        self.gcode.register_command('G11', self.cmd_G11)
        self.gcode.register_command('M103', self.cmd_G10)   # Add M103 and M101 aliases for G10 and G11
        self.gcode.register_command('M101', self.cmd_G11)
    
            
########################################################################################## Function to load the FirmwareRetraction class from the configuration file
def load_config(config):
    return FirmwareRetraction(config)
