

import time
import board,pwmio
from digitalio import DigitalInOut, Direction, Pull
from adafruit_motor import stepper
from adafruit_motor import servo
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import time
import usb_hid
import adafruit_hid
import math
import digitalio
import rotaryio


custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=1, usage=4)


# Stepper motor setup
DELAY = 0.0046  # fastest is ~ 0.004, 0.01 is still very smooth, gets steppy after that
FULL360 = 2048  # this is a full 360º (steps per revolution)

print ('DUTY IS ',str(2 ** 16))
## Declare the encoder, using a simple incremental this time
encoder = rotaryio.IncrementalEncoder(board.GP4,board.GP5)

## Declare Servo
#pwm = pwmio.PWMOut(board.GP16,frequency=50)
pwm = pwmio.PWMOut(board.GP16, duty_cycle=2 ** 15, frequency=50)


#myservo = servo.ContinuousServo(pwm)
myservo = servo.Servo(pwm)
#myservo.actuation_range=270
#myservo.min_pulse=640
#myservo.max_pulse=2400
#print (myservo)
## Declare motors
motors=[]
motor=dict()
motor['name']='altimeter'
motor['leftover']=0
motor['forward']=stepper.BACKWARD
motor['backward']=stepper.FORWARD
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
motor['forward']=stepper.FORWARD
motor['backward']=stepper.BACKWARD
motor['ratio']=(FULL360/39)
motor['coils'] = (
    DigitalInOut(board.GP13),  # A1
    DigitalInOut(board.GP11),  # A2
    DigitalInOut(board.GP12),  # B1
    DigitalInOut(board.GP10),  # B2
)
motors.append(motor)

motor=dict()
motor['name']='vspeed'
motor['leftover']=0
motor['forward']=None
motor['backward']=None
motor['ratio']=90/2000
motor['coils'] = None
motor['servo'] = myservo
motors.append(motor)




## Set motor pins as outputs and create steppers objects
for motor in motors:
    if motor['coils']:
        for coil in motor['coils']:
            coil.direction = Direction.OUTPUT
        motor['stepper']= stepper.StepperMotor(
            motor['coils'][0], motor['coils'][1], motor['coils'][2], motor['coils'][3], microsteps=None
        )
    else:
        motor['stepper']=None


def servo_move(theservo,myrange):
    print (theservo)
    print ('MY RANGE IS '+str(myrange))
    try:
        theservo.angle = myrange
        print ('TURNED IT')
    except Exception as e:
        print (str(e))

def stepper_move(mystepper,movedir):
    ## Move stepper one position in the indicated direction 'movedir'
    mystepper.onestep(direction=movedir)
    time.sleep(DELAY)

def rotate(motor,currval,newval):
    ## By leftover I mean anything that is in the decimal part, since the stepper does full steps, we need to carry on decimals for next movement.
    leftover = motor['leftover']
    #check first if it is stepper server
    if motor['stepper']:
        diff=currval-newval
        ## Calculate number of steps to do
        steps = abs((diff*motor['ratio']))+leftover
        # Rotate motor by the difference 'diff'
        mystepper=motor['stepper']
        ## And if it is a positive or negative roattion
        if diff >0:
            mydir = motor['forward']
        else:
            mydir = motor['backward']
        for n in range(1,steps):
            stepper_move(mystepper,mydir)
        ## Add leftover decimals
        motor['leftover'],discard=math.modf(steps)
    else:
        angle = 90+(motor['ratio']*newval)
        if angle >180:
            angle =180
        if angle <0:
            angle=0
        print ('for nevalue '+str(newval)+' THE RESULTING ANGLE IS '+str(angle))
        servo_move(motor['servo'],angle)
    return

def createEmptyReport():
    return [0]*2

def sendDeviceReport(report):
    custom_device.send_report(report,1)

def sendStop(value):
    ## This tells flighgear that correction is done, so creected values should be set to ZERO
    ## Vaue indiacates which bits need to be set (to simulate a button push)
    new_status = createEmptyReport()
    new_status[0]=value
    in_report = bytearray(new_status)  # copy in case we want to modify
    try:
        sendDeviceReport(in_report);  # in to computer    
    except Exception as e:
        print (str(e))
    new_status[0]=0
    in_report = bytearray(new_status)  # copy in case we want to modify
    try:
        sendDeviceReport(in_report);  # in to computer  
    except Exception as e:
        print (str(e) )
    return

def addToStatus (status,bit):
    ## Adds bit to status
    myposbits=[1,2,4,8,16,32,64,128]
    status = status | myposbits[bit]
    return status


print ('ROTATING SERVO TO 0 DEGREES')
servo_move(motors[2]['servo'],90)

## Create an array with all he possible inputs from FG
printout=[]
val = dict()
## ALTITUDE
val['name']='ALT'
val['digits']=[0,1,2,3,4]
val['currval']=0
val['motor']=0
val['corrector']=False
val['avoidzero']=False
printout.append(val)
val = dict()
## CORRECTED ALTITUDE
val['name']='CORRALT'
val['digits']=[5,6,7,8,9]
val['currval']=0
val['motor']=0
val['stoptrigger']=1
val['corrector']=True
printout.append(val)
val = dict()
## PRESSURE
val['name']='PRESSURE'
val['digits']=[10,11,12,13]
val['currval']=1027 ## TAKING 1027 as a good starting point
val['motor']=1
val['corrector']=False
val['avoidzero']=True ## Thisis done so it does not starts going back from 127 to zero at startup
printout.append(val)
val = dict()
## CORRECTED PRESSURE
val['name']='CORRPRESSURE'
val['digits']=[14,15,16,17]
val['currval']=0
val['motor']=1
val['stoptrigger']=2
val['corrector']=True
printout.append(val)
## PRESSURE
val['name']='VSPEED'
val['digits']=[18,19,20,21,22]
val['currval']=0 ## TAKING 1027 as a good starting point
val['motor']=2
val['corrector']=False
val['avoidzero']=True ## Thisis done so it does not starts going back from 127 to zero at startup
printout.append(val)
val = dict()
## CORRECTED PRESSURE
val['name']='CORRVSPEED'
val['digits']=[23,24,25,26,27]
val['currval']=0
val['motor']=2
val['stoptrigger']=16
val['corrector']=True
printout.append(val)
#Create in and out reports from HID
new_status = createEmptyReport()
out_report=[48]*28
last_position= 0
## Main loop
presses = 0
while True:
    dosend = False
    ## Get reports from FG
    bytereport = custom_device.get_last_received_report(2) # out from computer
    if bytereport:
        new_report=bytearray(bytereport)
        out_report=new_report
    else:
        out_report = None
    if out_report:
        ## Loop through reports to see if there's a match
        for currpo in printout:
            text=''
            for digit in currpo['digits']:
                text=text + chr(out_report[digit])
            try:
                newvalue = int(text)
            except:
                newvalue=currpo['currval']
            ## If there are value changes, act
            if newvalue!=currpo['currval']:
                if not currpo['corrector']:
                    if currpo['avoidzero'] and newvalue==0:
                        continue
                    else:
                        rotate(motors[currpo['motor']],newvalue,currpo['currval'])
                        currpo['currval']=newvalue
                else:
                    presses = presses+1
                    print ('CORRECTING '+currpo['name']+' BY '+str(newvalue)+' THIS IS FOR MOTOR '+str(currpo['motor'])+' FOR CLICK NUMBER '+str(presses))
                    currpo['currval']=0
                    rotate(motors[currpo['motor']],0,newvalue)
                    newvalue=0
                    for digit in currpo['digits']:
                       out_report[digit]=48
                    sendStop(currpo['stoptrigger'])
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
        sendDeviceReport(in_report);  # in to computer    
        new_status[0]=0
        in_report = bytearray(new_status)  # copy in case we want to modify
        sendDeviceReport(in_report);  # in to computer    
    time.sleep(0.01)

    