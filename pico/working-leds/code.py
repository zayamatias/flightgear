# This script supports the Raspberry Pi Pico board and the Lilygo ESP32-S2 board
# Raspberry Pi Pico: http://educ8s.tv/part/RaspberryPiPico
# ESP32-S2 Board: http://educ8s.tv/part/esp32s2
# OLED DISPLAY: https://educ8s.tv/part/OLED096

import board, busio, displayio, os, terminalio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import time
import usb_hid
import adafruit_hid
import board
import digitalio



displayio.release_displays()
sda, scl = board.GP0, board.GP1
i2c = busio.I2C(scl, sda)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)
custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=1, usage=4)


def addToStatus (status,bit):
    myposbits=[1,2,4,8,16,32,64,128]
    status = status | myposbits[bit]
    return status

'''

new_status = [0]*2

rotaries = [
            {'pins':[board.GP16,board.GP17],'bits':[0,1],'lvalue':True},
            {'pins':[board.GP18,board.GP19],'bits':[2,3],'lvalue':True},
            {'pins':[board.GP15,board.GP14],'bits':[4,5],'lvalue':True},
            {'pins':[board.GP13,board.GP12],'bits':[6,7],'lvalue':True},
            ]

dirpins = []*len(rotaries)
steppins = []*len(rotaries)


for rotary in rotaries:
    dirpins.append(digitalio.DigitalInOut(rotary['pins'][0]))
    steppins.append(digitalio.DigitalInOut(rotary['pins'][1]))
    dirpins[-1].direction=digitalio.Direction.INPUT
    steppins[-1].direction=digitalio.Direction.INPUT
    dirpins[-1].pull=digitalio.Pull.UP
    steppins[-1].pull=digitalio.Pull.UP


'''
font = bitmap_font.load_font("digital.bdf")


WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 5

# Make the display context
splash = displayio.Group()
#splashb = displayio.Group()
display.show(splash)


color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White

idx =0
value =0 
text ='NOTHING'
text_area = label.Label(
font, text=text, color=0xFFFFFF, x=0, y=HEIGHT // 2 - 1)
splash.append(text_area)
otext_area = text_area

#text_areab = label.Label(
#font, text=text, color=0xFFFFFF, x=0, y=HEIGHT // 2 - 1)
#splashb.append(text_areab)
#otext_areab = text_areab

printout=[]
val = dict()
val['name']='HDG'
val['digits']=[0,1,2]
printout.append(val)
val = dict()
val['name']='ALT'
val['digits']=[3,4,5,6,7]
printout.append(val)
val = dict()
val['name']='V/S'
val['digits']=[8,9,10,11,12]
printout.append(val)
val = dict()
val['name']='HPA'
val['digits']=[13,14,15,16]
printout.append(val)
val = dict()
val['name']='AIS'
val['digits']=[17,18,19,20]
printout.append(val)
val = dict()
val['name']='HDB'
val['digits']=[21,22,23]
printout.append(val)

pouidx =0
idx = 0
out_report=[48]*28
while True:

    #print ('WAITING FOR ACTION '+str(idx))

    #print ('GETTING REPORT')
    new_report = custom_device.get_last_received_report(0) # out from computer
    if new_report:
        out_report=new_report
    if out_report or idx==100:
        currpo = printout[pouidx]
        text =currpo['name']+' '
        for digit in currpo['digits']:
            text=text + chr(out_report[digit])
        text_area = label.Label(font, text=text, color=0xFFFFFF, x=0, y=HEIGHT // 2 - 1)
        splash.append(text_area)
        splash.remove(otext_area)
        otext_area = text_area

        if idx == 100:
            pouidx = pouidx +1
            if pouidx>len(printout)-1:
                pouidx=0
            idx=0
    '''
    idx =0
    dosend = False
    for rotary in rotaries:
        if rotary['lvalue'] != steppins[idx].value:
            if not steppins[idx].value:
                if not dirpins[idx].value:
                    print ('ROTARY '+str(idx)+' TO THE RIGHT')
                    new_status[0]=addToStatus(new_status[0],rotary['bits'][1])
                    dosend = True
                else:
                    print ('ROTARY '+str(idx)+' TO THE LEFT')
                    new_status[0]=addToStatus(new_status[0],rotary['bits'][0])
                    dosend = True
        rotary['lvalue']=steppins[idx].value
        idx = idx +1
    if dosend:
        in_report = bytearray(new_status)  # copy in case we want to modify
        custom_device.send_report(in_report,1);  # in to computer    
        print (new_status)   
        new_status[0]=0
        in_report = bytearray(new_status)  # copy in case we want to modify
        custom_device.send_report(in_report,1);  # in to computer    
   '''
    idx=idx+1
    time.sleep(0.1)
    