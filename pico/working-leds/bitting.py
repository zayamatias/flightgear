



def addToStatus (status,bit,value):
    myposbits=[1,2,4,8,16,32,64,128]
    mynegbits=[254,253,251,247,239,223,191,127]

    if value:
        status = status | myposbits[bit]
    else:
        status = status & mynegbits[bit]

    return status

status = 255
for b in range (0,8):
    status = addToStatus(status,b,True)
    print (b,status)
    status = addToStatus(status,b,False)
    print (b,status)