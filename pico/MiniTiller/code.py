

import time
import board,pwmio
from digitalio import DigitalInOut, Direction, Pull
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import time
import usb_hid
import adafruit_hid
import math
import digitalio
import rotaryio
import displayio
import busio



custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=1, usage=4)


## Declare the encoder, using a simple incremental this time
encoder = rotaryio.IncrementalEncoder(board.GP4,board.GP5)


## Declare Display
displayio.release_displays()
sda, scl = board.GP0, board.GP1
i2c = busio.I2C(scl, sda)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)
WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 5

# Make the display context
splash = displayio.Group()
#splashb = displayio.Group()
display.root_group=splash

font = bitmap_font.load_font("Digital-7-32.bdf")
color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White
idx =0
value =0 
text ='WAITING FG'
text_area = label.Label(font, text=text, color=0xFFFFFF, x=0, y=HEIGHT // 2 - 1)
text_area.anchor_point = (0.5,0.5) 
text_area.anchored_position = (WIDTH // 2, HEIGHT // 2)
splash.append(text_area)
otext_area = text_area


def createEmptyReport():
    return [0]*2

def sendDeviceReport(report):
    try:
        custom_device.send_report(report,1)
    except Exception as e:
        print(e)

def addToStatus (status,bit):
    ## Adds bit to status
    myposbits=[1,2,4,8,16,32,64,128]
    status = status | myposbits[bit]
    return status



new_status = createEmptyReport()
last_position= 999
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
        degrees=out_report[0]
        direction = out_report[1]
        text = str(degrees)
        if direction ==1:
            text = '  '+text +' >'
        if direction ==2:
            text = '< '+text+'  ' 
        text_area = label.Label(font, text=text, color=0xFFFFFF, x=0, y=HEIGHT // 2 - 1)
        text_area.anchor_point = (0.5,0.5) 
        text_area.anchored_position = (WIDTH // 2, HEIGHT // 2)
        splash.append(text_area)
        splash.remove(otext_area)
        otext_area = text_area
    x = encoder.position
    if x < last_position:
        new_status[0]=addToStatus(new_status[0],1)
        dosend = True
        last_position=x
    if x> last_position:
        new_status[0]=addToStatus(new_status[0],2)
        dosend = True
        last_position=x
    if dosend:
        in_report = bytearray(new_status)  # copy in case we want to modify
        sendDeviceReport(in_report);  # in to computer    
        new_status[0]=0
        in_report = bytearray(new_status)  # copy in case we want to modify
        sendDeviceReport(in_report);  # in to computer    

    time.sleep(0.01)
