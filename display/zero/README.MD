You first need to follow the instructions [here](https://randomnerdtutorials.com/raspberry-pi-zero-usb-keyboard-hid/#:~:text=4.-,Python%20Script,keyboard%20to%20the%20connected%20computer.&text=Copy%20and%20paste%20the%20next%20Python%20script%20to%20your%20Raspberry%20Pi.)

Instead of executing their hid descriptor, execute the one found in this repo (hid-descriptor.sh).

Copy the .xml file in the Event subdir into your event directory for FG.

Copy the files in the SD directory to your RPI (any directory should be ok as long as it is under /home/pi)

Launch the hid.py (sudo) in your RPI (it needs to be a W version to be connected to the internet, at least for the map downloading)

Good luck!
