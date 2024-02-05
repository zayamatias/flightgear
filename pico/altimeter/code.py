

import time
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_motor import stepper
import board, busio, displayio, os, terminalio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import time
import usb_hid
import adafruit_hid
import board
import math
import digitalio
import rotaryio


custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=1, usage=4)


# Stepper motor setup
DELAY = 0.0046  # fastest is ~ 0.004, 0.01 is still very smooth, gets steppy after that
FULL360 = 4096/2  # this is a full 360º


'''
rotaries = [
            {'dirpin':digitalio.DigitalInOut(board.GP4),
             'steppin':digitalio.DigitalInOut(board.GP5),
             'bits':[2,3]}
            ]


for rotary in rotaries:
    rotary['dirpin'].direction=digitalio.Direction.INPUT
    rotary['steppin'].direction=digitalio.Direction.INPUT
    rotary['dirpin'].pull=digitalio.Pull.UP
    rotary['steppin'].pull=digitalio.Pull.UP
'''
encoder = rotaryio.IncrementalEncoder(board.GP4,board.GP5)
currentaltitude=0
motors=[]
motor=dict()
motor['name']='altimeter'
motor['leftover']=0
motor['lastpath']=0
motor['ratio']=(FULL360/1000)
motor['coils'] = (
    DigitalInOut(board.GP21),  # A1
    DigitalInOut(board.GP19),  # A2
    DigitalInOut(board.GP20),  # B1
    DigitalInOut(board.GP18),  # B2
)
motors.append(motor)
motor=dict()
motor['name']='pressure'
motor['leftover']=0
motor['lastpath']=0
motor['ratio']=(FULL360/39)
motor['coils'] = (
    DigitalInOut(board.GP13),  # A1
    DigitalInOut(board.GP11),  # A2
    DigitalInOut(board.GP12),  # B1
    DigitalInOut(board.GP10),  # B2
)
motors.append(motor)
for motor in motors:
    for coil in motor['coils']:
        coil.direction = Direction.OUTPUT
    motor['stepper']= stepper.StepperMotor(
        motor['coils'][0], motor['coils'][1], motor['coils'][2], motor['coils'][3], microsteps=None
    )


def stepper_move(mystepper,movedir):
    mystepper.onestep(direction=movedir)
    time.sleep(DELAY)

def rotate(motor,diff):
    mystepper=motor['stepper']
    ## By leftover I mean anything that is in the decimal part, since the stepper does full steps, we need to carry on decimals for next movement.
    leftover = motor['leftover']
    lastpath = motor['lastpath']
    steps = abs((diff*motor['ratio']))+leftover
    if diff >0:
        mydir = stepper.FORWARD
    else:
        mydir = stepper.BACKWARD
    for n in range(1,steps):
        stepper_move(mystepper,mydir)
    motor['leftover'],discard=math.modf(steps)
    return

def sendStop(custom_device,value):
    new_status = [0]
    new_status[0]=value
    in_report = bytearray(new_status)  # copy in case we want to modify
    try:
        custom_device.send_report(in_report,0);  # in to computer    
    except Exception as e:
        print (str(e))
    new_status[0]=0
    in_report = bytearray(new_status)  # copy in case we want to modify
    try:
        custom_device.send_report(in_report,0);  # in to computer  
    except Exception as e:
        print (str(e) )
    return

def addToStatus (status,bit):
    myposbits=[1,2,4,8,16,32,64,128]
    status = status | myposbits[bit]
    return status

printout=[]
val = dict()
val['name']='ALT'
val['digits']=[0,1,2,3,4]
val['currval']=0
printout.append(val)
val = dict()
val['name']='CORRALT'
val['digits']=[5,6,7,8,9]
val['currval']=0
printout.append(val)
val = dict()
val['name']='PRESSURE'
val['digits']=[10,11,12,13]
val['currval']=1027 ## TAKING 1027 as a good starting point
printout.append(val)
val = dict()
val['name']='CORRPRESSURE'
val['digits']=[14,15,16,17]
val['currval']=0
printout.append(val)
new_status = [0]*2

out_report=[48]*28


last_position= 0
while True:
    dosend = False
    new_report = custom_device.get_last_received_report(2) # out from computer
    if new_report:
        out_report=new_report
    if out_report:
        for currpo in printout:
            text=''
            for digit in currpo['digits']:
                text=text + chr(out_report[digit])
            try:
                newvalue = int(text)
            except:
                newavalue=currpo['currval']
            if newvalue!=currpo['currval']:
                if currpo['name']=='ALT':
                    rotate(motors[0],newvalue-currpo['currval'])
                    currpo['currval']=newvalue
                if currpo['name']=='CORRALT':
                    currpo['currval']=newvalue
                    rotate(motors[0],newvalue)
                    sendStop(custom_device,1)
                if currpo['name']=='PRESSURE':
                    if newvalue!=0:
                        rotate(motors[1],newvalue-currpo['currval'])
                        currpo['currval']=newvalue
                if currpo['name']=='CORRPRESSURE':
                    currpo['currval']=newvalue
                    rotate(motors[1],newvalue)
                    sendStop(custom_device,2)
    x = encoder.position
    if x < last_position:
        new_status[0]=addToStatus(new_status[0],2)
        dosend = True
        last_position=x
    if x> last_position:
        new_status[0]=addToStatus(new_status[0],3)
        dosend = True
        last_position=x
    if dosend:
        in_report = bytearray(new_status)  # copy in case we want to modify
        custom_device.send_report(in_report,1);  # in to computer    
        new_status[0]=0
        in_report = bytearray(new_status)  # copy in case we want to modify
        custom_device.send_report(in_report,1);  # in to computer    
    time.sleep(0.05)

    