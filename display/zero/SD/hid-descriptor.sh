#!/usr/bin/env bash
# Snippet from https://github.com/girst/hardpass-sendHID/blob/master/README.md . In which, the following notice was left:

# this is a stripped down version of https://github.com/ckuethe/usbarmory/wiki/USB-Gadgets - I don't claim any rights

modprobe libcomposite
cd /sys/kernel/config/usb_gadget/
mkdir -p gadget.1
cd gadget.1
echo 0x239a > idVendor # Linux Foundation
echo 0x80f5 > idProduct # Multifunction Composite Gadget
echo 0x0100 > bcdDevice # v1.0.0
echo 0x0100 > bcdUSB # USB2
echo 0x00 > bDeviceClass
echo 0x00 > bDeviceSubClass
echo 0x00 > bDeviceProtocol
mkdir -p strings/0x409
##echo "deadbeef01234567890" > strings/0x409/serialnumber
echo "raspberrypi" > strings/0x409/manufacturer
echo "FGMOD" > strings/0x409/product

mkdir -p functions/hid.usb1
echo 0 > functions/hid.usb1/protocol
echo 0 > functions/hid.usb1/subclass
echo 0x1C > functions/hid.usb1/report_length
#echo "05010904A1010904A1020509850119012918150025019501751881020600FF09018502150026FF007508951C9102950175048101c0c0" | xxd -r -ps > functions/hid.usb1/report_desc
#echo "05010904A1010904A1020509850119012918150025017501951881020600FF09018502150026FF007508951C9102c0c0" | xxd -r -ps > functions/hid.usb1/report_desc
#echo "05010905A10105098501190129181500250175019518810205011581257F09300931093209357508950481020600FF09018502150026FF007508951C9102c0" | xxd -r -ps > functions/hid.usb1/report_desc
echo "05010904A1010904a1020509850119012918150025017501951881020600FF09018502150026FF00750895109102c0c0" | xxd -r -ps > functions/hid.usb1/report_desc
mkdir -p configs/c.1/strings/0x409
echo "Raspberry PI FGMOD For FlighGear" > configs/c.1/strings/0x409/configuration 
echo 100 > configs/c.1/MaxPower
echo 0x80 > configs/c.1/bmAttributes

ln -s functions/hid.usb1 configs/c.1/
ls /sys/class/udc > UDC
