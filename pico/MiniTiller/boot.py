# rawhid_boot.py --
# any changes here only reflected after board reset

import usb_hid
import supervisor

supervisor.set_usb_identification(product="MiniTiller")

REPORT_COUNT = 63  # size of report in bytes

CUSTOM_REPORT_DESCRIPTOR = bytes((
0x05, 0x01,        ## Usage Page (Sim Ctrls)
0x09, 0x04,        ## Usage (Flight Sim Dev)
0xA1, 0x01,        ## Collection (Application)
0x09, 0x04,        ##   Usage (Airplane Sim Dev)
0xA1, 0x02,        ##   Collection (Logical)
0x05, 0x09,        ##     Usage Page (Button)
0x85, 0x01,        ##     Report ID (1)
0x19, 0x01,        ##     Usage Minimum (0x01)
0x29, 0x08,        ##     Usage Maximum (0x01)
0x15, 0x00,        ##     Logical Minimum (0)
0x25, 0x01,        ##     Logical Maximum (1)
0x95, 0x08,        ##     Report Count (8)
0x75, 0x02,        ##     Report Size (1)
0x81, 0x02,        ##     Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
0x06, 0x00, 0xFF,  ##     Usage Page (Vendor Defined 0xFF00)
0x09, 0x01,        ##     Usage (0x01)
0x85, 0x02,        ##     Report ID (2)
0x15, 0x00,        ##     Logical Minimum (0)
0x25, 0xFF,        ##     Logical Maximum (-1)
0x75, 0x08,        ##     Report Size (8)
0x95, 0x02,        ##     Report Count (2)
0x91, 0x02,        ##     Output (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position,Non-volatile)
0xC0,              ##   End Collection
0xC0,              ## End Collection

## 53 bytes


## HDG(3) - HDGBUG(3) - ALT (5) - V/S (4) - HG(4) - KN (4) 

))

raw_hid = usb_hid.Device(
    report_descriptor=CUSTOM_REPORT_DESCRIPTOR,
    usage_page=0x1,         # Vendor defined
    usage=0x04,                # Vendor page 1
    report_ids=(1,2),
    out_report_lengths=(0,2),
    in_report_lengths=(2,0)
)

usb_hid.enable( (raw_hid,) )