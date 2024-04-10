
import pygame
import math

SCREEN_WIDTH, SCREEN_HEIGHT = 720, 576

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

alt1_path = "/home/pi/fgmod/images/alt1.png"  # Replace "example.png" with the path to your PNG image
alt1 = pygame.image.load(alt1_path)
alt1_rect = alt1.get_rect()
alt1_x = (SCREEN_WIDTH - 512) // 2
alt1_y = (SCREEN_HEIGHT - 512) // 2

hpg_x = (SCREEN_WIDTH - 384) // 2
hpg_y = (SCREEN_HEIGHT - 384) // 2

hpg_path = "/home/pi/fgmod/images/inhg.png"  # Replace "example.png" with the path to your PNG image
hpg_image = pygame.image.load(hpg_path)
hpg_w, hpg_h = hpg_image.get_size()


# Function to draw the altimeter
def blitRotate(surf, image, pos, originPos, angle):

    # offset from pivot to center
    image_rect = image.get_rect(topleft = (pos[0] - originPos[0], pos[1]-originPos[1]))
    offset_center_to_pivot = pygame.math.Vector2(pos) - image_rect.center
    
    # roatated offset from pivot to center
    rotated_offset = offset_center_to_pivot.rotate(-angle)

    # roatetd image center
    rotated_image_center = (pos[0] - rotated_offset.x, pos[1] - rotated_offset.y)

    # get a rotated image
    rotated_image = pygame.transform.rotate(image, angle)
    rotated_image_rect = rotated_image.get_rect(center = rotated_image_center)

    # rotate and blit the image
    surf.blit(rotated_image, rotated_image_rect)
  
def draw_altimeter(screen,values ):
    altitude,inhg = int(values[3]['value']),int(values[10]['value'])
    print(altitude)
    pos = (screen.get_width()/2, (screen.get_height()/2)+20)
    screen.fill((100, 100, 100))
    # Blit the image onto the screen
    hpg_rot =int((inhg-1050)*3)+110
    blitRotate(screen, hpg_image, pos, (hpg_w/2, hpg_h/2), hpg_rot)
    screen.blit(alt1, (alt1_x,alt1_y+20))
    draw_needles(screen,SCREEN_WIDTH,SCREEN_HEIGHT,altitude,1,1)

def rotate_around_point(xy, angle, center_x,center_y):
    angle_rad = math.radians(angle)
    
    # Extract coordinates of the point and the center
    x, y = xy
    
    
    # Calculate the distance from the center to the point
    dx = x - center_x
    dy = y - center_y
    
    # Apply rotation transformation
    rotated_x = center_x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
    rotated_y = center_y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
    
    return rotated_x, rotated_y

def rotate_shape(shape,angle,cx,cy):
    new_shape=[]
    for point in shape:
        new_x,new_y = rotate_around_point(point,angle,cx,cy)
        new_shape.append((new_x,new_y))
    return new_shape

def draw_needles(screen, sw,sh, value, interval, color):
    langle=(value % 1000)*.36
    mangle = ((value/1000)%10)*36
    sangle = ((value/10000)%10)*36
    cx=(sw//2)
    cy=(sh//2)
    large = [(cx-2,cy),(cx-5,cy-160),(cx, cy-180),(cx+5,cy-160),(cx+2, cy)]
    med = [(cx-2,cy),(cx-5,cy-130),(cx, cy-140),(cx+5,cy-130),(cx+2, cy)]
    small = [(cx-2,cy),(cx-5,cy-100),(cx, cy-110),(cx+5,cy-100),(cx+2, cy)]
    r_large = rotate_shape(large,langle,cx,cy)
    r_med = rotate_shape(med,mangle,cx,cy)
    r_small = rotate_shape(small,sangle,cx,cy)
    pygame.draw.polygon(screen, (255, 255, 255), r_small)
    pygame.draw.polygon(screen, (255, 255, 255), r_med)
    pygame.draw.polygon(screen, (255, 255, 255), r_large)
    return    