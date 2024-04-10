
import pygame
import math

SCREEN_WIDTH, SCREEN_HEIGHT = 720, 576

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)



ati1_img = pygame.image.load("/home/pi/fgmod/images/ati1.png")
ati1_rect = ati1_img.get_rect()
ati1_x = (SCREEN_WIDTH - 512) // 2
ati1_y = (SCREEN_HEIGHT - 512) // 2

ati2_img = pygame.image.load("/home/pi/fgmod/images/ati2.png")
ati2_rect = ati2_img.get_rect()
ati2_x = (SCREEN_WIDTH - 465) // 2 
ati2_y = (SCREEN_HEIGHT - 465) // 2
ati2_w, ati2_h = ati2_img.get_size()

ati3_img = pygame.image.load("/home/pi/fgmod/images/AI2.png")
ati3_rect = ati3_img.get_rect()
ati3_x = (SCREEN_WIDTH - 512) // 2
ati3_y = (SCREEN_HEIGHT - 512) // 2
ati3_w, ati3_h = ati3_img.get_size()

# Function to draw the altimeter
def blitRotate(surf, image, pos, originPos, angle,offset):

    # offset from pivot to center
    image_rect = image.get_rect(topleft = (pos[0] - originPos[0], pos[1]-originPos[1]))
    offset_center_to_pivot = pygame.math.Vector2(pos) - image_rect.center
    
    # roatated offset from pivot to center
    rotated_offset = offset_center_to_pivot.rotate(-angle)

    # roatetd image center
    rotated_image_center = (pos[0] - rotated_offset.x, pos[1] - rotated_offset.y + (offset*9))

    # get a rotated image
    rotated_image = pygame.transform.rotate(image, angle)
    rotated_image_rect = rotated_image.get_rect(center = rotated_image_center)

    # rotate and blit the image
    surf.blit(rotated_image, rotated_image_rect)
  


def draw_attitude(screen,myvalues):
    pitch,roll = int(myvalues[11]['value']),int(myvalues[12]['value'])
    print(pitch,roll)
    screen.fill((100, 100, 100))
    pos = (screen.get_width()/2, (screen.get_height()/2)+20)
    # Blit the image onto the screen
    blitRotate(screen, ati3_img, pos, (ati3_w/2, ati3_h/2), roll,pitch)
    blitRotate(screen, ati2_img, pos, (ati2_w/2, ati2_h/2), roll,0)
    
    screen.blit(ati1_img, (ati1_x,ati1_y))


def draw_needles(screen, sw,sh, value, interval, color):
    langle=value/110*180
    cx=(sw//2)
    cy=(sh//2)
    large = [(cx-5,cy),(cx-5,cy-160),(cx, cy-180),(cx+5,cy-160),(cx+5, cy)]
    r_large = rotate_shape(large,langle,cx,cy)
    pygame.draw.polygon(screen, (255, 255, 255), r_large)
    return    