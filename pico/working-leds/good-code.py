# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# You must add a gamepad HID device inside your boot.py file
# in order to use this example.
# See this Learn Guide for details:
# https://learn.adafruit.com/customizing-usb-devices-in-circuitpython/hid-devices#custom-hid-devices-3096614-9

import board
import digitalio
import analogio
import usb_hid

from hid_gamepad import Gamepad


myled = digitalio.DigitalInOut(board.GP15)
myled.direction = digitalio.Direction.OUTPUT


gp = Gamepad(usb_hid.devices)

# Create some buttons. The physical buttons are connected
# to ground on one side and these and these pins on the other.

button_pins = (board.GP13,board.GP14)

# Map the buttons to button numbers on the Gamepad.
# gamepad_buttons[i] will send that button number when buttons[i]
# is pushed.
gamepad_buttons = (1,2)

buttons = [digitalio.DigitalInOut(mypin) for mypin in button_pins]
for button in buttons:
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP

# Connect an analog two-axis joystick to A4 and A5.
ax = analogio.AnalogIn(board.A0)
ay = analogio.AnalogIn(board.A1)


# Equivalent of Arduino's map() function.
def range_map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

print ('---------------------------')
counter = 0
while True:
    # Buttons are grounded when pressed (.value = False).
    for i, button in enumerate(buttons):
        gamepad_button_num = gamepad_buttons[i]
        if button.value:
            gp.release_buttons(gamepad_button_num)
            #print(" release", gamepad_button_num, end="")
        else:
            gp.press_buttons(gamepad_button_num)
            #print(" press", gamepad_button_num, end="")

    rp = gp.getReport()
    print (rp)
    if rp: 
        myled.value=True
        print(rp)
        break
    


    # Convert range[0, 65535] to -127 to 127
    #gp.move_joysticks(
    #    x=range_map(ax.value, 0, 65535, -127, 127),
    #    y=range_map(ay.value, 0, 65535, -127, 127),
    #)
