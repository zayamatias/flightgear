# boot.py
import usb_hid

# This is only one example of a gamepad descriptor.
# It may not suit your needs, or be supported on your host computer.

GAMEPAD_REPORT_DESCRIPTOR = bytes((
    0x05, 0x01, 0x09, 0x04, 0xA1, 0x01, 0x05, 0x01, 0x09, 0x01, 0xA1, 0x00, 0x09, 0x30, 0x09, 0x31,
    0x15, 0x00, 0x26, 0xFF, 0x03, 0x95, 0x02, 0x75, 0x10, 0x81, 0x02, 0xC0, 0x05, 0x01, 0x09, 0x33,
    0x09, 0x34, 0x09, 0x35, 0x15, 0x00, 0x26, 0xFF, 0x03, 0x95, 0x03, 0x75, 0x10, 0x81, 0x02, 0x05,
    0x01, 0x09, 0x32, 0x15, 0x00, 0x26, 0xFF, 0x03, 0x95, 0x01, 0x75, 0x10, 0x81, 0x02, 0x05, 0x09,
    0x19, 0x01, 0x29, 0x30, 0x15, 0x00, 0x25, 0x01, 0x35, 0x00, 0x45, 0x01, 0x95, 0x30, 0x75, 0x01,
    0x81, 0x02, 0x06, 0x00, 0xFF, 0x19, 0x01, 0x29, 0x1C, 0x95, 0x1C, 0x75, 0x01, 0xB1, 0x02, 0x95,
    0x01, 0x75, 0x04, 0xB1, 0x01, 0xC0))

'''
bytes((
    0x05, 0x01,  # Usage Page (Generic Desktop Ctrls)
    0x09, 0x05,  # Usage (Game Pad)
    0xA1, 0x01,  # Collection (Application)

    0x05, 0x08, ## Usage page, page # for LED's
    0x19, 0x01, ## Usage minimum; 1
    0x29, 0x03, ## Usage maximum; 5
    0x91, 0x02, ## Output (Data, Variable, Absolute); LED report
    0x95, 0x01, ## Report count; 1
    0x75, 0x05, ## Report size; 3
    0x91, 0x01, ## Output (Constant); LED report padding

    0x85, 0x04,  #   Report ID (4)
    0x05, 0x09,  #   Usage Page (Button)
    0x19, 0x01,  #   Usage Minimum (Button 1)
    0x29, 0x10,  #   Usage Maximum (Button 16)
    0x15, 0x00,  #   Logical Minimum (0)
    0x25, 0x01,  #   Logical Maximum (1)
    0x75, 0x01,  #   Report Size (1)
    0x95, 0x10,  #   Report Count (16)
    0x81, 0x02,  #   Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x05, 0x01,  #   Usage Page (Generic Desktop Ctrls)
    0x15, 0x81,  #   Logical Minimum (-127)
    0x25, 0x7F,  #   Logical Maximum (127)
    0x09, 0x30,  #   Usage (X)
    0x09, 0x31,  #   Usage (Y)
    0x09, 0x32,  #   Usage (Z)
    0x09, 0x35,  #   Usage (Rz)
    0x75, 0x08,  #   Report Size (8)
    0x95, 0x04,  #   Report Count (4)
    0x81, 0x02,  #   Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0xC0,        # End Collection
))
'''
gamepad = usb_hid.Device(
    report_descriptor=GAMEPAD_REPORT_DESCRIPTOR,
    usage_page=0x01,           # Generic Desktop Control
    usage=0x05,                # Gamepad
    report_ids=(0,),           # Descriptor uses report ID 4.
    in_report_lengths=(52,),    # This gamepad sends 6 bytes in its report.
    out_report_lengths=(28,),   # It does receive reports.
)

usb_hid.disable()
### NO TOCAR LA COMA DESPUES DE GAMEPAD!!!!
usb_hid.enable((gamepad,))