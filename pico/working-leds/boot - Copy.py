# rawhid_boot.py --
# any changes here only reflected after board reset

import usb_hid

REPORT_COUNT = 63  # size of report in bytes

CUSTOM_REPORT_DESCRIPTOR = bytes((
0x05, 0x01,        ## Usage Page (Generic Desktop Ctrls)
0x09, 0x04,        ## Usage (Joystick)
0xA1, 0x01,        ## Collection (Application)
0x05, 0x09,        ##   Usage Page (Button)
0x85, 0x01,        # Report ID (1)
0x19, 0x01,        ##   Usage Minimum (0x01)
0x29, 0x30,        ##   Usage Maximum (0x30)
0x15, 0x00,        ##   Logical Minimum (0)
0x25, 0x01,        ##   Logical Maximum (1)
0x35, 0x00,        ##   Physical Minimum (0)
0x45, 0x01,        ##   Physical Maximum (1)
0x95, 0x30,        ##   Report Count (48)
0x75, 0x01,        ##   Report Size (1)
0x81, 0x02,        ##   Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
0x06, 0x00, 0xFF,  ##   Usage Page (Vendor Defined 0xFF00)
0x85, 0x01,        # Report ID (1)
0x09, 0x00,        # Usage Page (Undefined)
0x15, 0x00,        # Logical Minimum (0)
0x26, 0xFF, 0x00,  # Logical Maximum (255)
0x75, 0x08,        # Report Size (8 bits)
0x95, 28,           # Report Count (64 fields)
0x92, 0x02, 0x01,  # Input (Data,Var,Abs,Buf)0x09, 0x01,        ##   Usage (0x01)
0xC0,              ## End Collection

## 46 bytes
      ## End Collection

))

raw_hid = usb_hid.Device(
    report_descriptor=CUSTOM_REPORT_DESCRIPTOR,
    usage_page=0xff00,         # Vendor defined
    usage=0x01,                # Vendor page 1
    report_ids=(0,1),
    out_report_lengths=(0,28),
    in_report_lengths=(48,0)
)

usb_hid.enable( (raw_hid,) )