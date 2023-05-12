import os, io

class VirtualSD:
    def __init__(self, config):
        sd = "C:\\Users\\flopana\\Dropbox (Personal)\\3D Print\\AllPro3D_GIT\\klipper"
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd))
        self.current_file = "FW_Retraction_Input.gcode"
        self.file_position = self.file_size = 0
        self.next_file_position = 0
        self.cmd_from_sd = False
        self.must_pause_work = False

    def run(self):
        filename = self.current_file
        self._load_file(filename)
        self.work_handler()

    def _load_file(self, filename):
        fname = filename
        fname = os.path.join(self.sdcard_dirname, fname)
        f = io.open(fname, 'r', newline='')
        f.seek(0, os.SEEK_END)
        fsize = f.tell()
        f.seek(0)
        self.current_file = f
        self.file_position = 0
        self.file_size = fsize
        
    # Background work timer
    def work_handler(self):
        self.current_file.seek(self.file_position)
        partial_input = ""
        lines = []
        
        # Open Output file
        with open('FW_Retraction_Output.gcode', 'w') as output_file:
            # Read inout file and write output file
            while not self.must_pause_work:
                if not lines:
                    # Read more data
                    data = self.current_file.read(1024)
                    if not data:
                        # End of file
                        self.current_file.close()
                        break
                    lines = data.split('\n')
                    lines[0] = partial_input + lines[0]
                    partial_input = lines.pop()
                    lines.reverse()
                    continue
                # Dispatch command
                self.cmd_from_sd = True
                line = lines.pop()
                next_file_position = self.file_position + len(line) + 1
                self.next_file_position = next_file_position
                try:
                    #print(line)
                    output_file.write(line + '\n')
                except:
                    print("Error running gcode")
                    break
                self.cmd_from_sd = False
                self.file_position = self.next_file_position
            print("Done printing file")
            output_file.close()
        
vSD = VirtualSD({})

# Call the `run` method to load the file
vSD.run()
