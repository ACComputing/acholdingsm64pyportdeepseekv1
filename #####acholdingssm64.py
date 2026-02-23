import pygame
import math
import sys
from pygame.locals import *

# -------------------- Configuration --------------------
FPS = 60
WIDTH, HEIGHT = 800, 600
HALF_WIDTH, HALF_HEIGHT = WIDTH // 2, HEIGHT // 2

# SM64‑style speeds (adjusted for delta time)
MOVE_SPEED = 5.0      # units per second (was 0.08 per frame)
ROT_SPEED = 1.5       # radians per second (was 0.02 per frame)
CAMERA_HEIGHT = 2.0
CAMERA_DISTANCE = 5.0

# Colors
SKY_COLOR = (107, 140, 255)
GROUND_COLOR = (34, 139, 34)
CASTLE_COLOR = (255, 200, 220)
ROOF_COLOR = (70, 130, 180)
WINDOW_COLOR = (255, 215, 0)
DOOR_COLOR = (139, 69, 19)
PLAYER_COLOR = (255, 0, 0)
WIREFRAME_COLOR = (0, 0, 0)
MENU_BG = (50, 50, 150)
MENU_TEXT = (255, 255, 255)

# 3D constants
FOV = 90
NEAR = 0.1
FAR = 100.0

# -------------------- Vector math --------------------
def vec_add(v1, v2): return (v1[0]+v2[0], v1[1]+v2[1], v1[2]+v2[2])
def vec_sub(v1, v2): return (v1[0]-v2[0], v1[1]-v2[1], v1[2]-v2[2])
def vec_mul(v, s): return (v[0]*s, v[1]*s, v[2]*s)
def vec_dot(v1, v2): return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
def vec_cross(v1, v2):
    return (v1[1]*v2[2] - v1[2]*v2[1],
            v1[2]*v2[0] - v1[0]*v2[2],
            v1[0]*v2[1] - v1[1]*v2[0])
def vec_normalize(v):
    l = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    return (0,0,0) if l==0 else (v[0]/l, v[1]/l, v[2]/l)

# -------------------- 3D Object --------------------
class Object3D:
    def __init__(self, vertices, faces, colors, position=(0,0,0)):
        self.vertices = [vec_add(v, position) for v in vertices]
        self.faces = faces
        self.colors = colors
        self.position = position

    def move_to(self, new_pos):
        delta = vec_sub(new_pos, self.position)
        self.vertices = [vec_add(v, delta) for v in self.vertices]
        self.position = new_pos

# -------------------- Camera --------------------
def look_at(eye, target, up=(0,1,0)):
    forward = vec_normalize(vec_sub(target, eye))
    right = vec_normalize(vec_cross(forward, up))
    new_up = vec_cross(right, forward)
    return (right, new_up, forward, eye)

def world_to_camera(point, view):
    right, up, forward, eye = view
    p = vec_sub(point, eye)
    return (vec_dot(p, right), vec_dot(p, up), vec_dot(p, forward))

def project(point):
    x, y, z = point
    if z <= NEAR: return None
    f = 1 / math.tan(math.radians(FOV)/2)
    aspect = WIDTH / HEIGHT
    x_proj = (x * f) / (z * aspect)
    y_proj = (y * f) / z
    return (int(x_proj * HALF_WIDTH + HALF_WIDTH),
            int(-y_proj * HALF_HEIGHT + HALF_HEIGHT))

# -------------------- Build Castle (same geometry) --------------------
def create_castle():
    objects = []

    # Central Keep
    keep_pos = (0, 1.5, 0)
    kw, kh, kd = 3.0, 3.0, 3.0
    keep_vertices = [(-kw/2,0,-kd/2), (kw/2,0,-kd/2), (kw/2,kh,-kd/2), (-kw/2,kh,-kd/2),
                     (-kw/2,0,kd/2),  (kw/2,0,kd/2),  (kw/2,kh,kd/2),  (-kw/2,kh,kd/2)]
    keep_vertices = [vec_add(v, keep_pos) for v in keep_vertices]
    keep_faces = [[0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [1,2,6,5], [3,0,4,7]]
    keep_colors = [CASTLE_COLOR]*6
    objects.append(Object3D(keep_vertices, keep_faces, keep_colors))

    # Main Roof
    roof_height = 2.5
    roof_vertices = [(-kw/2,kh,-kd/2), (kw/2,kh,-kd/2), (kw/2,kh,kd/2), (-kw/2,kh,kd/2),
                     (0, kh+roof_height, 0)]
    roof_vertices = [vec_add(v, keep_pos) for v in roof_vertices]
    roof_faces = [[0,1,4], [1,2,4], [2,3,4], [3,0,4]]
    roof_colors = [ROOF_COLOR]*4
    objects.append(Object3D(roof_vertices, roof_faces, roof_colors))

    # Door
    door_w, door_h = 1.2, 2.0
    door_vertices = [(-door_w/2,0,-kd/2), (door_w/2,0,-kd/2),
                     (door_w/2,door_h,-kd/2), (-door_w/2,door_h,-kd/2)]
    door_vertices = [vec_add(v, keep_pos) for v in door_vertices]
    door_faces = [[0,1,2,3]]
    door_colors = [DOOR_COLOR]
    objects.append(Object3D(door_vertices, door_faces, door_colors))

    # Windows
    win_w, win_h = 0.5, 0.8
    for wx, wy in [(-1.0,1.5), (1.0,1.5), (-1.0,0.5), (1.0,0.5)]:
        win_verts = [(wx-win_w/2, wy-win_h/2, -kd/2), (wx+win_w/2, wy-win_h/2, -kd/2),
                     (wx+win_w/2, wy+win_h/2, -kd/2), (wx-win_w/2, wy+win_h/2, -kd/2)]
        win_verts = [vec_add(v, keep_pos) for v in win_verts]
        objects.append(Object3D(win_verts, [[0,1,2,3]], [WINDOW_COLOR]))

    # Left Tower (cylindrical)
    tower_pos = (-3.5, 1.0, -1.5)
    tr, th, seg = 1.2, 4.0, 10
    tv = []
    for i in range(seg):
        a = 2*math.pi*i/seg
        tv.append((tr*math.cos(a), 0, tr*math.sin(a)))
        tv.append((tr*math.cos(a), th, tr*math.sin(a)))
    tv = [vec_add(v, tower_pos) for v in tv]
    tf, tc = [], []
    for i in range(seg):
        j = (i+1)%seg
        i0,i1 = 2*i,2*i+1
        j0,j1 = 2*j,2*j+1
        tf.append([i0,j0,j1,i1]); tc.append(CASTLE_COLOR)
    apex = len(tv)
    tv.append(vec_add((0, th+1.5, 0), tower_pos))
    for i in range(seg):
        j = (i+1)%seg
        tf.append([2*i+1,2*j+1,apex]); tc.append(ROOF_COLOR)
    objects.append(Object3D(tv, tf, tc))

    # Right Tower (mirror)
    tower_pos2 = (3.5, 1.0, -1.5)
    tv2 = []
    for i in range(seg):
        a = 2*math.pi*i/seg
        tv2.append((tr*math.cos(a), 0, tr*math.sin(a)))
        tv2.append((tr*math.cos(a), th, tr*math.sin(a)))
    tv2 = [vec_add(v, tower_pos2) for v in tv2]
    tf2, tc2 = [], []
    for i in range(seg):
        j = (i+1)%seg
        i0,i1 = 2*i,2*i+1
        j0,j1 = 2*j,2*j+1
        tf2.append([i0,j0,j1,i1]); tc2.append(CASTLE_COLOR)
    apex2 = len(tv2)
    tv2.append(vec_add((0, th+1.5, 0), tower_pos2))
    for i in range(seg):
        j = (i+1)%seg
        tf2.append([2*i+1,2*j+1,apex2]); tc2.append(ROOF_COLOR)
    objects.append(Object3D(tv2, tf2, tc2))

    # Central Back Tower
    ct_pos = (0, 2.0, 2.5)
    cr, ch = 1.5, 5.0
    cv = []
    for i in range(seg):
        a = 2*math.pi*i/seg
        cv.append((cr*math.cos(a), 0, cr*math.sin(a)))
        cv.append((cr*math.cos(a), ch, cr*math.sin(a)))
    cv = [vec_add(v, ct_pos) for v in cv]
    cf, cc = [], []
    for i in range(seg):
        j = (i+1)%seg
        i0,i1 = 2*i,2*i+1
        j0,j1 = 2*j,2*j+1
        cf.append([i0,j0,j1,i1]); cc.append(CASTLE_COLOR)
    spire = len(cv)
    cv.append(vec_add((0, ch+2.0, 0), ct_pos))
    for i in range(seg):
        j = (i+1)%seg
        cf.append([2*i+1,2*j+1,spire]); cc.append(ROOF_COLOR)
    objects.append(Object3D(cv, cf, cc))

    # Bushes
    bush_verts = [(-0.3,0,-0.3),(0.3,0,-0.3),(0.3,0.6,-0.3),(-0.3,0.6,-0.3),
                  (-0.3,0,0.3),(0.3,0,0.3),(0.3,0.6,0.3),(-0.3,0.6,0.3)]
    bush_faces = [[0,1,2,3],[4,5,6,7],[0,1,5,4],[2,3,7,6],[1,2,6,5],[3,0,4,7]]
    bush_colors = [(34,139,34)]*6
    for pos in [(2,0.3,3), (-2,0.3,3), (3,0.3,-4), (-3,0.3,-4), (0,0.3,5)]:
        objects.append(Object3D(bush_verts, bush_faces, bush_colors, pos))

    return objects

# -------------------- Player --------------------
def create_player(pos):
    size = 0.8
    verts = [(-size/2,0,-size/2),(size/2,0,-size/2),(size/2,size,-size/2),(-size/2,size,-size/2),
             (-size/2,0,size/2),(size/2,0,size/2),(size/2,size,size/2),(-size/2,size,size/2)]
    faces = [[0,1,2,3],[4,5,6,7],[0,1,5,4],[2,3,7,6],[1,2,6,5],[3,0,4,7]]
    colors = [PLAYER_COLOR]*6
    return Object3D(verts, faces, colors, pos)

# -------------------- Collision (AABB) --------------------
def check_collision(new_pos, objects, radius=0.8):
    px, py, pz = new_pos
    hr = radius/2
    for obj in objects:
        xs = [v[0] for v in obj.vertices]
        ys = [v[1] for v in obj.vertices]
        zs = [v[2] for v in obj.vertices]
        if (px-hr < max(xs) and px+hr > min(xs) and
            py-hr < max(ys) and py+hr > min(ys) and
            pz-hr < max(zs) and pz+hr > min(zs)):
            return True
    return False

# -------------------- Simple Frustum Culling --------------------
def is_face_visible(cam_verts, face):
    # Check if any vertex is in front of near plane (simple culling)
    for idx in face:
        if cam_verts[idx][2] > NEAR:
            return True
    return False

# -------------------- Menu --------------------
def show_menu(screen):
    font = pygame.font.Font(None, 74)
    title = font.render("Super Mario 64", True, MENU_TEXT)
    subtitle = pygame.font.Font(None, 36).render("Peach's Castle", True, MENU_TEXT)
    start_font = pygame.font.Font(None, 50)
    start_text = start_font.render("Press SPACE to Start", True, MENU_TEXT)
    quit_text = start_font.render("Press ESC to Quit", True, MENU_TEXT)

    while True:
        screen.fill(MENU_BG)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 230))
        screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, 350))
        screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, 420))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == QUIT: return False
            if e.type == KEYDOWN:
                if e.key == K_SPACE: return True
                if e.key == K_ESCAPE: return False

# -------------------- Game Loop --------------------
def game_loop(screen):
    clock = pygame.time.Clock()
    castle_objects = create_castle()
    player = create_player((0, 0.5, 8))
    player_angle = 0.0

    # Ground grid (now drawn with lines, but we'll use a simpler approach)
    grid_size = 20
    grid_step = 1

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # delta time in seconds

        for e in pygame.event.get():
            if e.type == QUIT: return False
            if e.type == KEYDOWN and e.key == K_ESCAPE: return True

        keys = pygame.key.get_pressed()
        move_dir = [0, 0, 0]

        # Movement scaled by delta time
        if keys[K_UP] or keys[K_w]:
            move_dir[0] -= MOVE_SPEED * dt * math.sin(player_angle)
            move_dir[2] -= MOVE_SPEED * dt * math.cos(player_angle)
        if keys[K_DOWN] or keys[K_s]:
            move_dir[0] += MOVE_SPEED * dt * math.sin(player_angle)
            move_dir[2] += MOVE_SPEED * dt * math.cos(player_angle)
        if keys[K_LEFT] or keys[K_a]:
            move_dir[0] -= MOVE_SPEED * dt * math.sin(player_angle + math.pi/2)
            move_dir[2] -= MOVE_SPEED * dt * math.cos(player_angle + math.pi/2)
        if keys[K_RIGHT] or keys[K_d]:
            move_dir[0] -= MOVE_SPEED * dt * math.sin(player_angle - math.pi/2)
            move_dir[2] -= MOVE_SPEED * dt * math.cos(player_angle - math.pi/2)
        if keys[K_q]:
            player_angle += ROT_SPEED * dt
        if keys[K_e]:
            player_angle -= ROT_SPEED * dt

        new_pos = vec_add(player.position, move_dir)
        if not check_collision(new_pos, castle_objects):
            player.move_to(new_pos)

        # Camera behind player
        cam_offset = (CAMERA_DISTANCE * math.sin(player_angle),
                      CAMERA_HEIGHT,
                      CAMERA_DISTANCE * math.cos(player_angle))
        cam_pos = vec_add(player.position, cam_offset)
        view = look_at(cam_pos, player.position)

        # Prepare render list with culling
        render_objects = castle_objects + [player]
        faces_to_draw = []

        for obj in render_objects:
            cam_verts = [world_to_camera(v, view) for v in obj.vertices]
            for fi, face in enumerate(obj.faces):
                if not is_face_visible(cam_verts, face):
                    continue
                proj_points = []
                depth_sum = 0
                valid = True
                for idx in face:
                    pt = project(cam_verts[idx])
                    if pt is None:
                        valid = False
                        break
                    proj_points.append(pt)
                    depth_sum += cam_verts[idx][2]
                if valid:
                    depth = depth_sum / len(face)
                    faces_to_draw.append((depth, obj.colors[fi], proj_points))

        faces_to_draw.sort(key=lambda x: x[0], reverse=True)

        # Draw
        screen.fill(SKY_COLOR)

        # Ground grid (optimized: draw only a few lines)
        for i in range(-grid_size, grid_size+1, grid_step):
            p1 = world_to_camera((i, 0, -grid_size), view)
            p2 = world_to_camera((i, 0,  grid_size), view)
            sp1, sp2 = project(p1), project(p2)
            if sp1 and sp2:
                pygame.draw.line(screen, (100,100,100), sp1, sp2, 1)

            p1 = world_to_camera((-grid_size, 0, i), view)
            p2 = world_to_camera(( grid_size, 0, i), view)
            sp1, sp2 = project(p1), project(p2)
            if sp1 and sp2:
                pygame.draw.line(screen, (100,100,100), sp1, sp2, 1)

        for depth, color, points in faces_to_draw:
            if len(points) >= 3:
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, WIREFRAME_COLOR, points, 1)

        pygame.display.flip()

    return False

# -------------------- Main --------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("Super Mario 64 - Peach's Castle (60 FPS)")

    while True:
        if not show_menu(screen):
            break
        if not game_loop(screen):
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
