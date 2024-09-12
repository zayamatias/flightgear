

Printing the gyroscope / Heading indicator

You'll need a 3D printer for this (for obvious reasons). Download the 3D model [3D Altimeter](https://www.printables.com/model/356101-gyro-compass-heading-indicator-for-flight-simulati)

I had to make some changes due to the encoder being different, you can find those adaptations [here](https://www.printables.com/model/745500-altimeter-modifcation-of-two-pieces-from-original-)

Soldering

Once you've built the Heading Indicator, time to solder everything to the controller. For the controller, I'm using an RPI [Pico](https://thepihut.com/products/raspberry-pi-pico) W, any RPI Pico should work anyway (just check the pins in case they are different)

Gyroscope

![Circuit diagram](https://github.com/zayamatias/flightgear/blob/main/pico/altimeter/Altimeter_bb.png?raw=true)

The 5V external power supply is optional in case your USB power output is not enough to power 2 stepper motors.

Installing the software

Download the [CircuitPython](https://circuitpython.org/downloads) distribution that corresponds to your bard and install it.

Copy boot.py and code.py from the repo into the file (connect the RPI via USB and it will appear as a CIRUITPY drive/folder)

Copy the file under Event into your flightgear Events home directory (usually ~/.fgfs/Input/Event/.)

Now if you launch flightgear and everything is soldered properly, the altimeter will start to move as soon as the plane of choice starts loading


Calibrating the Heading Indicator

The Heading Indicator has no way (as far as I'm able to do it) to know which is its exact position, so you have to manually calibrate it so the starting position is the same as the starting position in the sim. To do so press the slash '/' key to open the properties navigator. search for 'rpi' then 'heading' then 'correctors'. You will see 2 values you can modify, heading and headingbug, enter the value in degrees yo want to correct (plus or minus) until the altimeter shows everything as in the plane's cockpit.

Nice Flying!


