
import pygame
import math

SCREEN_WIDTH, SCREEN_HEIGHT = 720, 576

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

alt1_path = "/home/pi/fgmod/images/vsi1.png"  # Replace "example.png" with the path to your PNG image
alt1 = pygame.image.load(alt1_path)
alt1_rect = alt1.get_rect()
alt1_x = (SCREEN_WIDTH - 512) // 2
alt1_y = (SCREEN_HEIGHT - 512) // 2


# Function to draw the altimeter
  
def draw_vsi(screen, myvalues):
    vs = int(myvalues[4]['value'])
    print(vs)
    pos = (screen.get_width()/2, (screen.get_height()/2)+20)
    screen.fill((100, 100, 100))
    # Blit the image onto the screen
    screen.blit(alt1, (alt1_x,alt1_y+20))
    draw_needles(screen,SCREEN_WIDTH,SCREEN_HEIGHT,vs,1,1)

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
    langle=value/2000*180
    cx=(sw//2)
    cy=(sh//2)
    large = [(cx,cy-5),(cx-160,cy-5),(cx-180, cy),(cx-160,cy+5),(cx, cy+5)]
    r_large = rotate_shape(large,langle,cx,cy)
    pygame.draw.polygon(screen, (255, 255, 255), r_large)
    return    