# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import usb_hid
from adafruit_hid.mouse import Mouse

mouse = Mouse(usb_hid.devices)

# define buttons. these can be any physical switches/buttons, but the values
# here work out-of-the-box with a CircuitPlayground Express' A and B buttons.
up = digitalio.DigitalInOut(board.D4)
up.direction = digitalio.Direction.INPUT
up.pull = digitalio.Pull.DOWN

down = digitalio.DigitalInOut(board.D5)
down.direction = digitalio.Direction.INPUT
down.pull = digitalio.Pull.DOWN

while True:
    time.sleep(0.1)
    mouse.move(wheel=10)
    time.sleep(0.1)
    mouse.move(wheel=-10)
