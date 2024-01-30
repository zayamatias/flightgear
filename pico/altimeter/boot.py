# rawhid_boot.py --
# any changes here only reflected after board reset

import usb_hid
import supervisor

supervisor.set_usb_identification(product="Altimeter")

REPORT_COUNT = 63  # size of report in bytes

CUSTOM_REPORT_DESCRIPTOR = bytes((
0x05, 0x01,          ## USAGE_PAGE = Generic Desktop (USAGE_PAGE is much like a namespace, see "HID Usage" in the specs)
0x09, 0x04,          ## USAGE = Mouse (one of the available usages from the selected USAGE_PAGE)
0xa1, 0x01,          ## COLLECTION = Application (Allows you to define different groups of related attributes etc)
0x09, 0x04,          ##   USAGE = Pointer (an available sub USAGE of the parent USAGE)
0xa1, 0x02,          ##   COLLECTION = Physical (Allows you to define different groups of related attributes etc)
0x05, 0x09,          ##     USAGE_PAGE = Button (a change of USAGE_PAGE, like moving to a new namespace)
#0x85, 0x01,          # Report ID (1)
0x19, 0x01,          ##     USAGE_MINIMUM = Button 1 (specifying the buttons)
0x29, 0x10,          ##     USAGE_MAXIMUM = Button 3 (specifying the buttons)
0x15, 0x00,          ##     LOGICAL_MINIMUM = 0 (the min value that can be reported)
0x25, 0x01,          ##     LOGICAL_MAXIMUM = 1 (the max value that can be reported)
0x95, 0x10,          ##     REPORT_COUNT = 16 (total number of reported data fields, in this case the number of buttons)
0x75, 0x01,          ##     REPORT_SIZE = 1 (bits used per report field, size will be 3 fields x 1 bit = 3 bits))
0x81, 0x02,          ##     INPUT = Data,Var,Abs (add the above data variables to the report)
0x06, 0x00, 0xFF,    ##     USAGE_PAGE = Generic Desktop (returning USAGE_PAGE back again)
0x09, 0x01,          # Usage Page (Undefined)
#0x85, 0x02,          # Report ID (1)
0x15, 0x00,          ##     LOGICAL_MINIMUM = 0
0x25, 0xFF,          ##     LOGICAL_MAXIMUM = 255
0x75, 0x08,          ##     REPORT_SIZE = 
0x95, 28,        ##     REPORT_COUNT =
0xB1, 0x02,        ##   Feature (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position,Non-volatile)
0x95, 0x01,        ##   Report Count (1)
0x75, 0x04,        ##   Report Size (4)
0xB1, 0x01,        ##
0xc0,                ##   END_COLLECTION
0xc0,                ## END_COLLECTION

## HDG(3) - HDGBUG(3) - ALT (5) - V/S (4) - HG(4) - KN (4) 

))

raw_hid = usb_hid.Device(
    report_descriptor=CUSTOM_REPORT_DESCRIPTOR,
    usage_page=0x1,         # Vendor defined
    usage=0x04,                # Vendor page 1
    report_ids=(0,),
    out_report_lengths=(28,),
    in_report_lengths=(1,)
)

usb_hid.enable( (raw_hid,) )