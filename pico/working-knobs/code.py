import usb_hid
import adafruit_hid
import board
import digitalio

custom_device = adafruit_hid.find_device(usb_hid.devices, usage_page=1, usage=4)

print("custom_device: %04x %04x" % (custom_device.usage_page, custom_device.usage) )


def addToStatus (status,bit):
    myposbits=[1,2,4,8,16,32,64,128]
    status = status | myposbits[bit]
    return status


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


while True:
    #print ('WAITING FOR ACTION '+str(idx))

    #print ('GETTING REPORT')
    out_report = custom_device.get_last_received_report(2) # out from computer
    #print ('GOT REPORT')
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

           
    #if out_report:
    #    print("len:",len(out_report),["%02x" % x for x in out_report])

