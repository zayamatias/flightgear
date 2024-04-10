import time
import sys
import random
import struct
import socket
import pygame
import requests
from io import BytesIO
from PIL import Image
import math
import os
from pathlib import Path
from stopit import SignalTimeout as Timeout
import altimeter
import vsi
import ias
import attitude
import struct

pygame.display.init()
info = pygame.display.Info()
print (info)
#print(info)
SCREEN_WIDTH, SCREEN_HEIGHT = 720,576
TWOTO31 = 2147483648
TWOTO32 = 4294967296

#print ('LAUNCHING')
def load_tile(x, y, zoom):
    if (x, y, zoom) in loaded_tiles:
        return loaded_tiles[(x, y, zoom)]
    else:
        print ('LOADING TILES FROM THE INTERNET')
        url = base_url.format(zoom, x, y)
        headers = {'User-Agent': 'FGMapper/0.1'}
        response = requests.get(url, headers=headers)
        tile_image = pygame.image.load(BytesIO(response.content))
        loaded_tiles[(x, y, zoom)] = tile_image
        print ('LOADED TILES FROM THE INTERNET')
        return tile_image

def lat_lon_to_screen_coords(lat, lon,zoom,size):
    n = 2 ** zoom
    lat_rad = math.radians(lat)
    xtile = (lon + 180.0) / 360.0 * n
    ytile = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    screen_x = ((xtile - int(xtile)) * tile_size)
    screen_y =((ytile - int(ytile)) * tile_size)  
    return int(screen_x), int(screen_y)

# Function to convert latitude and longitude to tile coordinates
def lat_lon_to_tile_coords(lat, lon, zoom):
    n = 2 ** zoom
    lat_rad = math.radians(lat)
    myx = (lon + 180.0) / 360.0 * n
    myy = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    xtile = math.floor(myx)
    ytile = math.floor(myy)
    xoff = int((myx-xtile)*tile_size)
    yoff = int((myy-ytile)*tile_size)
    return xtile, ytile,xoff,yoff

def draw_airplane(lat,lon,heading,tx,ty):
    ox,oy=lat_lon_to_screen_coords(lat, lon,zoom,tile_size)
    rotated_image, rotated_rect = rotate_image(airplane_image, 360-heading)
    screen.blit(rotated_image,(tx+int(ox),ty+int(oy)))
        
def show_image(myimage):
    screen.blit(myimage,(0,0))
    pygame.display.flip()

def update_screen(screen,values):

    screen.fill((0,0,0))
    font = pygame.font.SysFont('Arial', 25)
    startx=0
    starty=0
    counter=0
    for value in values:
        pygame.draw.rect(screen, (100,100,100), (startx, starty, 200, 50), 2)
        screen.blit(font.render(str(value['name']), True, (255,0,0)), (startx+10, starty+10))
        screen.blit(font.render(str(value['value']), True, (255,0,0)), (startx+10, starty+30))
        starty = starty + 60
        counter = counter + 1
        if counter ==8:
            starty=0
            startx = startx +220
            counter =0
    pygame.display.update()
    
def update_map(screen,myvalues):
    latitude, longitude,heading = myvalues[0]['value'],myvalues[1]['value'],myvalues[5]['value']
    print (latitude, longitude,heading)
    # Clear the screen
    screen.fill((255, 255, 255))

    # Calculate tile coordinates for the center of the screen
    center_tile_x, center_tile_y,off_x,off_y = lat_lon_to_tile_coords(latitude, longitude, zoom)

    # Calculate the range of tiles to load based on screen dimensions
    tiles_x = math.floor(SCREEN_WIDTH / tile_size)
    tiles_y = math.floor(SCREEN_HEIGHT / tile_size)

    # Load and blit map tiles
    for y in range((-tiles_y // 2), (tiles_y // 2)+1):
        for x in range((-tiles_x // 2) , (tiles_x // 2)+1):
            tile_x = center_tile_x + x
            tile_y = center_tile_y + y
            number_font  = pygame.font.SysFont( None, 16 )                # Default font, Size 16
            number_image = number_font.render( str(tile_x)+'/'+str(tile_y), True, (0,0,0), (255,255,255))  # Number 8
            tile_image = load_tile(tile_x, tile_y, zoom)
            screen_x = ((x + tiles_x // 2) * tile_size)
            screen_y = ((y + tiles_y // 2) * tile_size)
            screen.blit(tile_image, (screen_x, screen_y))
            screen.blit(number_image,[screen_x, screen_y, 5,5])
            if tile_x == center_tile_x and tile_y == center_tile_y:
                draw_airplane(latitude,longitude,heading,screen_x,screen_y)
                pygame.draw.rect(tile_image,(0, 0, 255),[0, 0, 256, 256],4)
            else:
                pygame.draw.rect(tile_image,(255, 0, 0),[0, 0, 256, 256],1)
    return off_x,off_y

def rotate_image(image, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=original_rect.center)
    return rotated_image, new_rect


# Open the device file
def write_report(report):
    res = None 
    with Timeout(5) as timeout_ctx:
        with open('/dev/hidg0', 'rb+') as fd:
            #print ('AAAA')
            res = fd.write(report)
            #print ('BBB')
        #print('CCCCC')
    return res

def read_report(size):
    res = None
    with Timeout(1) as timeout_ctx:
        with open('/dev/hidg0', 'rb') as fd:
            res = fd.read(size)
    return res

def decode_bytes(mybytes):
    #print(mybytes)
    v = 0
    b = 1
    for i in range(0,5):
        #print (v,'+(',mybytes[4-i],'-65)*',b)
        v += (mybytes[4-i] - 65) * b
        b *= 128
    if v / TWOTO31 >= 1:
        v -= TWOTO32
    return int(v)
  


#print ('INIT')

pygame.init()

#print ('AFTER INIT')


# Set screen dimensions

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.mouse.set_visible(False)

#print ('SCREEN CREATED')
# Define map parameters
zoom = 13
tile_size = 256
base_url ="https://tile.openstreetmap.org/{}/{}/{}.png"
loaded_tiles = {}

# Main loop
running = True
lastlat = 0.0
lastlon = 0.0
airplane_image = pygame.image.load("/home/pi/fgmod/images/airplane.png")
splash_image = pygame.image.load("/home/pi/fgmod/images/splash.png")
show_image(splash_image)
original_rect = airplane_image.get_rect()
airplane_position = [int(SCREEN_WIDTH/2), int(SCREEN_HEIGHT/2)]

values = []
values.append(dict(name='LAT',value=0))
values.append(dict(name='LON',value=0))
values.append(dict(name='IAS',value=0))
values.append(dict(name='ALT',value=0))
values.append(dict(name='V/S',value=0))
values.append(dict(name='HDG',value=0))
values.append(dict(name='COM1',value=0))
values.append(dict(name='COM2',value=0))
values.append(dict(name='NAV1',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='HPA',value=0))
values.append(dict(name='PITCH',value=0))
values.append(dict(name='ROLL',value=0))
values.append(dict(name='TRATE',value=0))
values.append(dict(name='SLSK',value=0))

values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))
values.append(dict(name='NAV2',value=0))

#print (values)
reportreqs =[[1,1],[2,1],[4,1],[8,1],[16,1],[32,1],[64,1],[128,1],[1,2],[2,2],[4,2],[8,2],[16,2],[32,2],[64,2],[128,2],[1,3],[2,3],[4,3],[8,3],[16,3],[32,3],[64,3],[128,3]]
# Read data from the device

dispscreens=[]
dispscreens.append(dict(name='ALL VALUES',values=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23],function=update_screen))
dispscreens.append(dict(name='MAP',values=[0,1,5],function=update_map))
dispscreens.append(dict(name='ALTIMETER',values=[3,10],function=altimeter.draw_altimeter))
dispscreens.append(dict(name='IAS',values=[2],function=ias.draw_ias))
dispscreens.append(dict(name='VSI',values=[4],function=vsi.draw_vsi))
dispscreens.append(dict(name='ATTITUDE',values=[11,12],function=attitude.draw_attitude))

initial = 0
##print ('Initializing')
#while not initial:
#    with open('/dev/hidg0', 'rb+') as fd:
#        res = fd.write(bytearray([0,0,0,0]))
#    initial = Path('/dev/hidg0').stat().st_size
#    #print(initial)
##print (initial)
#print ('GOING TO LOOP')
in_report = [0]*4
in_report[0]=1
#try:
while True:
    
    for dispscreen in dispscreens:
        timer = 100
        while timer >0:
            for reportreq in dispscreen['values']:
                in_report = [0]*4
                in_report[0]=1
                in_report[reportreqs[reportreq][1]]= reportreqs[reportreq][0]
                my_bytearray = bytearray(in_report)
                res = None
                while not res:
                    res = write_report(my_bytearray)
                data = None
                while not data:
                    data = read_report(17)  # Adjust buffer size as per your requirement
                    if int(data[1])!=reportreq:
                        data =None
                intdata=[]
                for mydata in data:
                    intdata.append(int(mydata))
                intpart = decode_bytes([data[2],data[3],data[4],data[5],data[6]])
                decpart = decode_bytes([data[7],data[8],data[9],data[10],data[11]]) / TWOTO31
                print (reportreq,intpart,decpart)
                values[reportreq]['value']=intpart+decpart
            myfunction = dispscreen['function']
            myfunction(screen,values)
            ##  I NEED TO EXECUTE THE ACTUAL FUNCTION
            pygame.display.flip()
            timer -= 1
    '''        


    valpos = 0
    #print ('STARTED LOOP')
    for rrq in reportreqs:
        #print ('NEXT LOOP ',valpos)
        in_report = [0]*4
        in_report[0]=1
        in_report[rrq[1]]= rrq[0]
        my_bytearray = bytearray(in_report)
        #print ('GOING TO WRITE ',in_report)
        res = write_report(my_bytearray)
        if not res:
            #print ('WRITE TIMEOUT')
            continue
        #print ('DID WRITE')
        #print ('GOING TO READ')
        print ('START READ')
        data = read_report(17)  # Adjust buffer size as per your requirement
        print('END READ')
        if not data:
            print ('READ TIMEOUT')
            continue
        ## PARSE DATA INTO VALUES 
        currbyte = 1
        intdata=[]
        for mydata in data:
            intdata.append(int(mydata))
            
        print("read")
        intpart = decode_bytes([data[2],data[3],data[4],data[5],data[6]])
        decpart = decode_bytes([data[7],data[8],data[9],data[10],data[11]]) / TWOTO31
        values[valpos]['value']=intpart+decpart
        
        print (values[valpos]['name'],values[valpos]['value'])
        valpos=valpos+1
        currbyte=currbyte+10
    #print ('DID READ')
        #print ('INT DATA ',data[1])
    #print ('CREATED VALUES')   0,0,0,58,185

    #print(longitude,latitude)
    #print ('GOING TO CHECK')
    #print ('GOING TO UPDATE MAP')
    #update_screen(values)
    #update_map(values[0]['value'],values[1]['value'],values[5]['value'])
    # Update the display
    #altimeter.draw_altimeter(screen,int(values[3]['value']),values[10]['value'])
    vsi.draw_vsi(screen,int(values[4]['value']))
    #ias.draw_ias(screen,int(values[2]['value']))
    #attitude.draw_attitude(screen,int(values[11]['value']),int(values[12]['value']))
    pygame.display.flip()
#except Exception as e:
#    exc_type, exc_obj, exc_tb = sys.exc_info()
#    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
#    print(exc_type, fname, exc_tb.tb_lineno,e)
# Close the device file
#hid_device.close()

'''