import usb_hid
import adafruit_hid
import board
import digitalio

custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=0xff00, usage=1)

print("custom_device: %04x %04x" % (custom_device.usage_page, custom_device.usage) )

new_status = [0]*48
old_status = [0]*48

dirPin = digitalio.DigitalInOut(board.GP16)
stepPin = digitalio.DigitalInOut(board.GP17)
dirPin.direction=digitalio.Direction.INPUT
stepPin.direction=digitalio.Direction.INPUT

dirPin.pull = digitalio.Pull.UP
stepPin.pull = digitalio.Pull.UP

previousValue = True

idx =0

while True:
    #print ('WAITING FOR ACTION '+str(idx))

    #print ('GETTING REPORT')
    out_report = custom_device.get_last_received_report(2) # out from computer
    #print ('GOT REPORT')
    if previousValue != stepPin.value:
        idx=idx+1
        if not stepPin.value:
            if not dirPin.value:
                print ('LEFT BUTTON '+str(idx))
                new_status[0]=1
            else:
                print ('RIGHT BUTTON '+str(idx))
                new_status[0]=2
        else:
            print ('RESETTING')
            new_status[0]=0
        previousValue=stepPin.value
        #print ('CREATING REPORT')
        in_report = bytearray(new_status)  # copy in case we want to modify
        #print ('SENDING REPORT')
        custom_device.send_report(in_report, 1);  # in to computer       
        #print ('SENT REPORT')
        #old_status=new_status.copy()
           
    #if out_report:
    #    print("len:",len(out_report),["%02x" % x for x in out_report])

