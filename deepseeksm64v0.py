import pygame
import math
import sys
from pygame.locals import *

# -------------------- Configuration --------------------
FPS = 60
WIDTH, HEIGHT = 800, 600
HALF_WIDTH, HALF_HEIGHT = WIDTH // 2, HEIGHT // 2

# Movement speed (Famicom-style: a bit slower)
MOVE_SPEED = 0.08
ROT_SPEED = 0.02
CAMERA_HEIGHT = 2.0      # camera height above player
CAMERA_DISTANCE = 5.0    # distance behind player

# Colors (closer to SM64's Peach's Castle)
SKY_COLOR = (107, 140, 255)      # brighter blue
GROUND_COLOR = (34, 139, 34)      # forest green
CASTLE_COLOR = (255, 200, 220)    # peach/pink
ROOF_COLOR = (70, 130, 180)       # steel blue (more accurate than tan)
WINDOW_COLOR = (255, 215, 0)      # gold for windows/accents
DOOR_COLOR = (139, 69, 19)        # saddle brown
PLAYER_COLOR = (255, 0, 0)        # red for Mario
WIREFRAME_COLOR = (0, 0, 0)

# 3D constants
FOV = 90
NEAR = 0.1
FAR = 100.0

# -------------------- Vector math helpers --------------------
def vec_add(v1, v2):
    return (v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2])

def vec_sub(v1, v2):
    return (v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2])

def vec_mul(v, s):
    return (v[0] * s, v[1] * s, v[2] * s)

def vec_dot(v1, v2):
    return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]

def vec_normalize(v):
    length = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if length == 0: return (0,0,0)
    return (v[0]/length, v[1]/length, v[2]/length)

def vec_cross(v1, v2):
    return (v1[1]*v2[2] - v1[2]*v2[1],
            v1[2]*v2[0] - v1[0]*v2[2],
            v1[0]*v2[1] - v1[1]*v2[0])

# -------------------- 3D Object class --------------------
class Object3D:
    def __init__(self, vertices, faces, colors, position=(0,0,0)):
        self.vertices = [vec_add(v, position) for v in vertices]  # world vertices
        self.faces = faces          # list of lists of vertex indices
        self.colors = colors         # color per face
        self.position = position

    def move_to(self, new_pos):
        delta = vec_sub(new_pos, self.position)
        self.vertices = [vec_add(v, delta) for v in self.vertices]
        self.position = new_pos

# -------------------- Camera functions --------------------
def look_at(eye, target, up=(0,1,0)):
    """Build a view matrix (as a tuple of basis vectors and translation)"""
    forward = vec_normalize(vec_sub(target, eye))
    right = vec_normalize(vec_cross(forward, up))
    new_up = vec_cross(right, forward)  # orthonormal basis
    return (right, new_up, forward, eye)

def world_to_camera(point, view):
    right, up, forward, eye = view
    p = vec_sub(point, eye)
    x = vec_dot(p, right)
    y = vec_dot(p, up)
    z = vec_dot(p, forward)
    return (x, y, z)

def project(point):
    """Perspective projection, returns (x,y) or None if behind camera"""
    x, y, z = point
    if z <= NEAR:
        return None
    f = 1 / math.tan(math.radians(FOV)/2)
    aspect = WIDTH / HEIGHT
    x_proj = (x * f) / (z * aspect)
    y_proj = (y * f) / z
    screen_x = int(x_proj * HALF_WIDTH + HALF_WIDTH)
    screen_y = int(-y_proj * HALF_HEIGHT + HALF_HEIGHT)
    return (screen_x, screen_y)

# -------------------- Create Castle and World Objects (Accurate SM64 Peach's Castle) --------------------
def create_castle():
    objects = []

    # --- Central Keep (main building) ---
    keep_pos = (0, 1.5, 0)
    keep_width, keep_height, keep_depth = 3.0, 3.0, 3.0
    keep_vertices = [
        (-keep_width/2, 0, -keep_depth/2), ( keep_width/2, 0, -keep_depth/2),
        ( keep_width/2, keep_height, -keep_depth/2), (-keep_width/2, keep_height, -keep_depth/2),
        (-keep_width/2, 0,  keep_depth/2), ( keep_width/2, 0,  keep_depth/2),
        ( keep_width/2, keep_height,  keep_depth/2), (-keep_width/2, keep_height,  keep_depth/2)
    ]
    keep_vertices = [vec_add(v, keep_pos) for v in keep_vertices]

    keep_faces = [
        [0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [1,2,6,5], [3,0,4,7]
    ]
    keep_colors = [CASTLE_COLOR]*6
    objects.append(Object3D(keep_vertices, keep_faces, keep_colors))

    # Main roof (pointed spire - like a tall pyramid)
    roof_height = 2.5
    roof_vertices = [
        (-keep_width/2, keep_height, -keep_depth/2), ( keep_width/2, keep_height, -keep_depth/2),
        ( keep_width/2, keep_height,  keep_depth/2), (-keep_width/2, keep_height,  keep_depth/2),
        (0, keep_height + roof_height, 0)  # apex
    ]
    roof_vertices = [vec_add(v, keep_pos) for v in roof_vertices]
    roof_faces = [[0,1,4], [1,2,4], [2,3,4], [3,0,4]]
    roof_colors = [ROOF_COLOR]*4
    objects.append(Object3D(roof_vertices, roof_faces, roof_colors))

    # --- Front Entrance (arch) ---
    # Simple door as a brown rectangle on front face
    door_width, door_height = 1.2, 2.0
    door_center = (0, 0.8, -keep_depth/2)  # front face center
    door_vertices = [
        (-door_width/2, 0, -keep_depth/2), ( door_width/2, 0, -keep_depth/2),
        ( door_width/2, door_height, -keep_depth/2), (-door_width/2, door_height, -keep_depth/2)
    ]
    door_vertices = [vec_add(v, keep_pos) for v in door_vertices]  # relative to keep
    door_faces = [[0,1,2,3]]
    door_colors = [DOOR_COLOR]
    objects.append(Object3D(door_vertices, door_faces, door_colors))

    # Add a small arch above door (simulate with a half-cylinder? Not easy; we'll add a half-octagon)
    arch_radius = 0.8
    arch_height = door_height + 0.3
    arch_vertices = []
    arch_segments = 6
    for i in range(arch_segments+1):
        angle = math.pi * i / arch_segments  # 0 to pi
        x = arch_radius * math.cos(angle - math.pi/2)  # adjust so it curves outward
        y = arch_height + arch_radius * math.sin(angle)
        arch_vertices.append((x, y, -keep_depth/2))
    # Move to center
    arch_vertices = [vec_add(v, keep_pos) for v in arch_vertices]
    # We need to create a face (strip) connecting these points? For simplicity, just draw as a thin polygon? But we can't easily. Skip for now.

    # --- Windows (stained glass) ---
    # Add small colored squares on front face around door
    win_w, win_h = 0.5, 0.8
    for (wx, wy) in [(-1.0, 1.5), (1.0, 1.5), (-1.0, 0.5), (1.0, 0.5)]:
        win_vertices = [
            (wx - win_w/2, wy - win_h/2, -keep_depth/2), (wx + win_w/2, wy - win_h/2, -keep_depth/2),
            (wx + win_w/2, wy + win_h/2, -keep_depth/2), (wx - win_w/2, wy + win_h/2, -keep_depth/2)
        ]
        win_vertices = [vec_add(v, keep_pos) for v in win_vertices]
        win_faces = [[0,1,2,3]]
        win_colors = [WINDOW_COLOR]
        objects.append(Object3D(win_vertices, win_faces, win_colors))

    # --- Left Tower (cylindrical with conical roof) ---
    tower_pos = (-3.5, 1.0, -1.5)
    tower_radius = 1.2
    tower_height = 4.0
    segments = 10  # more segments for smoother appearance
    tower_vertices = []
    # Create cylinder walls
    for i in range(segments):
        angle = 2*math.pi*i/segments
        x = tower_radius * math.cos(angle)
        z = tower_radius * math.sin(angle)
        tower_vertices.append((x, 0, z))
        tower_vertices.append((x, tower_height, z))
    tower_vertices = [vec_add(v, tower_pos) for v in tower_vertices]

    tower_faces = []
    tower_colors = []
    for i in range(segments):
        j = (i+1)%segments
        i0 = 2*i
        i1 = 2*i+1
        j0 = 2*j
        j1 = 2*j+1
        tower_faces.append([i0, j0, j1, i1])
        tower_colors.append(CASTLE_COLOR)

    # Conical roof
    roof_base_verts = [2*i+1 for i in range(segments)]  # top ring indices
    # Add apex vertex
    apex_idx = len(tower_vertices)
    tower_vertices.append(vec_add((0, tower_height + 1.5, 0), tower_pos))
    for i in range(segments):
        j = (i+1)%segments
        tri_face = [roof_base_verts[i], roof_base_verts[j], apex_idx]
        tower_faces.append(tri_face)
        tower_colors.append(ROOF_COLOR)

    objects.append(Object3D(tower_vertices, tower_faces, tower_colors))

    # --- Right Tower (mirror) ---
    tower_pos2 = (3.5, 1.0, -1.5)
    tower_vertices2 = []
    for i in range(segments):
        angle = 2*math.pi*i/segments
        x = tower_radius * math.cos(angle)
        z = tower_radius * math.sin(angle)
        tower_vertices2.append((x, 0, z))
        tower_vertices2.append((x, tower_height, z))
    tower_vertices2 = [vec_add(v, tower_pos2) for v in tower_vertices2]

    tower_faces2 = []
    tower_colors2 = []
    for i in range(segments):
        j = (i+1)%segments
        i0 = 2*i
        i1 = 2*i+1
        j0 = 2*j
        j1 = 2*j+1
        tower_faces2.append([i0, j0, j1, i1])
        tower_colors2.append(CASTLE_COLOR)

    apex_idx2 = len(tower_vertices2)
    tower_vertices2.append(vec_add((0, tower_height + 1.5, 0), tower_pos2))
    for i in range(segments):
        j = (i+1)%segments
        tri_face = [2*i+1, 2*j+1, apex_idx2]
        tower_faces2.append(tri_face)
        tower_colors2.append(ROOF_COLOR)

    objects.append(Object3D(tower_vertices2, tower_faces2, tower_colors2))

    # --- Central Tower (behind main keep, taller) ---
    center_tower_pos = (0, 2.0, 2.5)
    ct_radius = 1.5
    ct_height = 5.0
    ct_vertices = []
    for i in range(segments):
        angle = 2*math.pi*i/segments
        x = ct_radius * math.cos(angle)
        z = ct_radius * math.sin(angle)
        ct_vertices.append((x, 0, z))
        ct_vertices.append((x, ct_height, z))
    ct_vertices = [vec_add(v, center_tower_pos) for v in ct_vertices]

    ct_faces = []
    ct_colors = []
    for i in range(segments):
        j = (i+1)%segments
        i0 = 2*i
        i1 = 2*i+1
        j0 = 2*j
        j1 = 2*j+1
        ct_faces.append([i0, j0, j1, i1])
        ct_colors.append(CASTLE_COLOR)

    # Spire roof
    spire_height = 2.0
    apex_idx_ct = len(ct_vertices)
    ct_vertices.append(vec_add((0, ct_height + spire_height, 0), center_tower_pos))
    for i in range(segments):
        j = (i+1)%segments
        tri_face = [2*i+1, 2*j+1, apex_idx_ct]
        ct_faces.append(tri_face)
        ct_colors.append(ROOF_COLOR)

    objects.append(Object3D(ct_vertices, ct_faces, ct_colors))

    # --- Small decorative cubes (like hedges or pillars) ---
    cube_vertices = [(-0.3,0,-0.3), (0.3,0,-0.3), (0.3,0.6,-0.3), (-0.3,0.6,-0.3),
                     (-0.3,0,0.3), (0.3,0,0.3), (0.3,0.6,0.3), (-0.3,0.6,0.3)]
    cube_faces = [[0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [1,2,6,5], [3,0,4,7]]
    cube_colors = [(34,139,34)]*6  # green

    for pos in [(2,0.3,3), (-2,0.3,3), (3,0.3,-4), (-3,0.3,-4), (0,0.3,5)]:
        objects.append(Object3D(cube_vertices, cube_faces, cube_colors, pos))

    return objects

# -------------------- Player Object --------------------
def create_player(pos):
    size = 0.8
    vertices = [
        (-size/2, 0, -size/2), ( size/2, 0, -size/2), ( size/2, size, -size/2), (-size/2, size, -size/2),
        (-size/2, 0,  size/2), ( size/2, 0,  size/2), ( size/2, size,  size/2), (-size/2, size,  size/2)
    ]
    faces = [[0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [1,2,6,5], [3,0,4,7]]
    colors = [PLAYER_COLOR]*6
    return Object3D(vertices, faces, colors, pos)

# -------------------- Collision Detection (AABB) --------------------
def check_collision(new_pos, objects, player_radius=0.8):
    px, py, pz = new_pos
    p_half = player_radius / 2
    for obj in objects:
        xs = [v[0] for v in obj.vertices]
        ys = [v[1] for v in obj.vertices]
        zs = [v[2] for v in obj.vertices]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        minz, maxz = min(zs), max(zs)
        if (px - p_half < maxx and px + p_half > minx and
            py - p_half < maxy and py + p_half > miny and
            pz - p_half < maxz and pz + p_half > minz):
            return True
    return False

# -------------------- Main Game Loop --------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Super Mario 64 - Accurate Peach's Castle (Pygame 3D)")
    clock = pygame.time.Clock()

    castle_objects = create_castle()
    player_start = (0, 0.5, 8)
    player = create_player(player_start)
    player_angle = 0.0

    grid_size = 20
    grid_step = 1

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        move_dir = [0, 0, 0]

        if keys[K_UP] or keys[K_w]:
            move_dir[0] -= MOVE_SPEED * math.sin(player_angle)
            move_dir[2] -= MOVE_SPEED * math.cos(player_angle)
        if keys[K_DOWN] or keys[K_s]:
            move_dir[0] += MOVE_SPEED * math.sin(player_angle)
            move_dir[2] += MOVE_SPEED * math.cos(player_angle)
        if keys[K_LEFT] or keys[K_a]:
            move_dir[0] -= MOVE_SPEED * math.sin(player_angle + math.pi/2)
            move_dir[2] -= MOVE_SPEED * math.cos(player_angle + math.pi/2)
        if keys[K_RIGHT] or keys[K_d]:
            move_dir[0] -= MOVE_SPEED * math.sin(player_angle - math.pi/2)
            move_dir[2] -= MOVE_SPEED * math.cos(player_angle - math.pi/2)
        if keys[K_q]:
            player_angle += ROT_SPEED
        if keys[K_e]:
            player_angle -= ROT_SPEED

        new_pos = vec_add(player.position, move_dir)
        if not check_collision(new_pos, castle_objects):
            player.move_to(new_pos)

        # Camera
        cam_offset = (CAMERA_DISTANCE * math.sin(player_angle),
                      CAMERA_HEIGHT,
                      CAMERA_DISTANCE * math.cos(player_angle))
        cam_pos = vec_sub(player.position, cam_offset)
        target = player.position
        view = look_at(cam_pos, target)

        # Prepare scene
        render_objects = castle_objects + [player]
        faces_to_draw = []

        for obj in render_objects:
            cam_verts = [world_to_camera(v, view) for v in obj.vertices]
            for face_idx, face in enumerate(obj.faces):
                proj_points = []
                valid = True
                depth_sum = 0
                for idx in face:
                    pt = project(cam_verts[idx])
                    if pt is None:
                        valid = False
                        break
                    proj_points.append(pt)
                    depth_sum += cam_verts[idx][2]
                if not valid:
                    continue
                depth = depth_sum / len(face)
                faces_to_draw.append((depth, obj.colors[face_idx], proj_points))

        faces_to_draw.sort(key=lambda x: x[0], reverse=True)

        # Render
        screen.fill(SKY_COLOR)

        # Ground grid
        for i in range(-grid_size, grid_size+1, grid_step):
            p1 = world_to_camera((i, 0, -grid_size), view)
            p2 = world_to_camera((i, 0, grid_size), view)
            sp1, sp2 = project(p1), project(p2)
            if sp1 and sp2:
                pygame.draw.line(screen, (100,100,100), sp1, sp2, 1)

            p1 = world_to_camera((-grid_size, 0, i), view)
            p2 = world_to_camera((grid_size, 0, i), view)
            sp1, sp2 = project(p1), project(p2)
            if sp1 and sp2:
                pygame.draw.line(screen, (100,100,100), sp1, sp2, 1)

        for depth, color, points in faces_to_draw:
            if len(points) >= 3:
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, WIREFRAME_COLOR, points, 1)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
