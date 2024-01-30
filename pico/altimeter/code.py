

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
import digitalio


custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=1, usage=4)

# Stepper motor setup
DELAY = 0.0046  # fastest is ~ 0.004, 0.01 is still very smooth, gets steppy after that
FULL360 = 4096/2  # this is a full 360º
LEFTOVER = 0
LASTPATH = 0
currentaltitude=0

coils = (
    DigitalInOut(board.GP21),  # A1
    DigitalInOut(board.GP19),  # A2
    DigitalInOut(board.GP20),  # B1
    DigitalInOut(board.GP18),  # B2
)
for coil in coils:
    coil.direction = Direction.OUTPUT

stepper_motor = stepper.StepperMotor(
    coils[0], coils[1], coils[2], coils[3], microsteps=None
)


def move(steps):
    for n in range (0,steps+1):
        stepper_fwd()

def stepper_fwd():
    stepper_motor.onestep(direction=stepper.FORWARD)
    time.sleep(DELAY)
    #stepper_motor.release()


def stepper_back():
    stepper_motor.onestep(direction=stepper.BACKWARD)
    time.sleep(DELAY)
    #stepper_motor.release()

def calculateSteps(angle):
    steps= round(FULL360/360*angle)
    return steps

def calculateDelta(oldangle,newangle):
    countercw = newangle - oldangle
    clockwise = 360 - countercw
    
    if clockwise<countercw:
        return clockwise
    else:
        return -1*(countercw)

def rotateHDG(diff):
    #print ('DIFF '+str(diff))
    global LEFTOVER
    global LASTPATH
    if LASTPATH:
        steps = (diff*(FULL360/1000))+LEFTOVER
    else:
        steps = (diff*(FULL360/1000))-LEFTOVER

    print ('ROTATING '+str(steps)+' STEPS')
    if steps>0:
        for n in range(1,steps):
            print ('ROTATE FWD '+str(n))
            LASTPATH = 1
            stepper_fwd()
    else:
        for n in range(steps,1):
            print ('ROTATE BWD '+str(n))
            LASTPATH = 0 
            stepper_back()
    ##Since the steps are integers and not decimal, if we do not carry what was left to the next turn then there will be a desadjustment
    LEFTOVER=steps % 1
    return

def sendStop(custom_device):
    new_status = [0]
    new_status[0]=1
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

out_report=[48]*28
while True:
    new_report = custom_device.get_last_received_report(0) # out from computer
    if new_report:
        out_report=new_report
        #print ('NEW REPORT RECEIVED')
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
                if currpo['name']!='CORRALT':
                    print ('ROTATING BY: '+str(newvalue-currpo['currval']))
                    rotateHDG(newvalue-currpo['currval'])
                    currpo['currval']=newvalue
                else:
                    print ('CORRECTING BY: '+str(newvalue-currpo['currval']))
                    currpo['currval']=newvalue
                    rotateHDG(newvalue)
                    sendStop(custom_device)
    time.sleep(0.01)
    