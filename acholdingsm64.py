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

# Colors
SKY_COLOR = (135, 206, 235)   # sky blue
GROUND_COLOR = (34, 139, 34)  # forest green
CASTLE_COLOR = (255, 200, 220) # peach/pink
ROOF_COLOR = (210, 180, 140)   # tan
PLAYER_COLOR = (255, 0, 0)     # red for Mario
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

    # View transformation: translate and rotate to camera space
    # We'll apply manually in transform function
    return (right, new_up, forward, eye)

def world_to_camera(point, view):
    right, up, forward, eye = view
    # Translate
    p = vec_sub(point, eye)
    # Rotate to align with camera axes
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
    # Map to screen coordinates
    screen_x = int(x_proj * HALF_WIDTH + HALF_WIDTH)
    screen_y = int(-y_proj * HALF_HEIGHT + HALF_HEIGHT)  # flip Y
    return (screen_x, screen_y)

# -------------------- Create Castle and World Objects --------------------
def create_castle():
    objects = []

    # Main keep (big cube + roof pyramid)
    keep_pos = (0, 1.5, 0)  # centered at y=1.5 so bottom at y=0
    keep_vertices = [
        (-1.5, 0, -1.5), ( 1.5, 0, -1.5), ( 1.5, 3, -1.5), (-1.5, 3, -1.5),  # front face
        (-1.5, 0,  1.5), ( 1.5, 0,  1.5), ( 1.5, 3,  1.5), (-1.5, 3,  1.5)   # back face
    ]
    # Move to keep_pos
    keep_vertices = [vec_add(v, keep_pos) for v in keep_vertices]

    # Faces (indices) and colors
    keep_faces = [
        [0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [1,2,6,5], [3,0,4,7]
    ]
    keep_colors = [CASTLE_COLOR]*6
    objects.append(Object3D(keep_vertices, keep_faces, keep_colors))

    # Roof (pyramid on top)
    roof_height = 1.5
    roof_vertices = [
        (-1.5, 3, -1.5), ( 1.5, 3, -1.5), ( 1.5, 3,  1.5), (-1.5, 3,  1.5),  # base
        (0, 3+roof_height, 0)  # apex
    ]
    roof_vertices = [vec_add(v, keep_pos) for v in roof_vertices]
    roof_faces = [
        [0,1,4], [1,2,4], [2,3,4], [3,0,4]  # triangular sides
    ]
    roof_colors = [ROOF_COLOR]*4
    objects.append(Object3D(roof_vertices, roof_faces, roof_colors))

    # Left tower (cylinder approximated by octagon prism)
    tower_pos = (-3, 1, -2)
    tower_radius = 1.0
    tower_height = 3.0
    tower_vertices = []
    segments = 8
    for i in range(segments):
        angle = 2*math.pi*i/segments
        x = tower_radius * math.cos(angle)
        z = tower_radius * math.sin(angle)
        tower_vertices.append((x, 0, z))
        tower_vertices.append((x, tower_height, z))
    # Add center points for roof? We'll just do a cone roof
    # But for simplicity, add a flat roof
    tower_vertices = [vec_add(v, tower_pos) for v in tower_vertices]
    tower_faces = []
    tower_colors = []
    # Wall faces
    for i in range(segments):
        j = (i+1)%segments
        # Quad connecting bottom i, bottom j, top j, top i
        i0 = 2*i
        i1 = 2*i+1
        j0 = 2*j
        j1 = 2*j+1
        tower_faces.append([i0, j0, j1, i1])
        tower_colors.append(CASTLE_COLOR)
    # Roof (flat)
    # Add a top polygon
    top_face = [2*i+1 for i in range(segments)]
    tower_faces.append(top_face)
    tower_colors.append(ROOF_COLOR)
    objects.append(Object3D(tower_vertices, tower_faces, tower_colors))

    # Right tower (similar)
    tower_pos2 = (3, 1, -2)
    tower_vertices2 = []
    for i in range(segments):
        angle = 2*math.pi*i/segments
        x = tower_radius * math.cos(angle)
        z = tower_radius * math.sin(angle)
        tower_vertices2.append((x, 0, z))
        tower_vertices2.append((x, tower_height, z))
    tower_vertices2 = [vec_add(v, tower_pos2) for v in tower_vertices2]
    tower_faces2 = []
    for i in range(segments):
        j = (i+1)%segments
        i0 = 2*i
        i1 = 2*i+1
        j0 = 2*j
        j1 = 2*j+1
        tower_faces2.append([i0, j0, j1, i1])
    tower_faces2.append([2*i+1 for i in range(segments)])
    tower_colors2 = [CASTLE_COLOR]*segments + [ROOF_COLOR]
    objects.append(Object3D(tower_vertices2, tower_faces2, tower_colors2))

    # Add a few small cubes around as decoration
    cube_vertices = [
        (-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 1, -0.5), (-0.5, 1, -0.5),
        (-0.5, 0, 0.5), (0.5, 0, 0.5), (0.5, 1, 0.5), (-0.5, 1, 0.5)
    ]
    cube_faces = [[0,1,2,3], [4,5,6,7], [0,1,5,4], [2,3,7,6], [1,2,6,5], [3,0,4,7]]
    cube_colors = [CASTLE_COLOR]*6

    # Place a few
    for pos in [(1, 0.5, 3), (-1, 0.5, 3), (2, 0.5, -4), (-2, 0.5, -4)]:
        obj = Object3D(cube_vertices, cube_faces, cube_colors, pos)
        objects.append(obj)

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
    # Simple bounding box check against all static objects
    # player bounding box: from new_pos - (r, r, r) to new_pos + (r, r, r) but we only check horizontal and vertical
    # We'll just check if any object's bounding box overlaps
    px, py, pz = new_pos
    p_half = player_radius / 2
    for obj in objects:
        # Compute object AABB
        xs = [v[0] for v in obj.vertices]
        ys = [v[1] for v in obj.vertices]
        zs = [v[2] for v in obj.vertices]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        minz, maxz = min(zs), max(zs)
        # Check overlap
        if (px - p_half < maxx and px + p_half > minx and
            py - p_half < maxy and py + p_half > miny and
            pz - p_half < maxz and pz + p_half > minz):
            return True
    return False

# -------------------- Main Game Loop --------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Super Mario 64 - Peach's Castle (Pygame 3D)")
    clock = pygame.time.Clock()

    # Create world
    castle_objects = create_castle()
    player_start = (0, 0.5, 8)  # in front of castle
    player = create_player(player_start)
    player_angle = 0.0  # radians, 0 = facing -Z (into screen)

    # Ground grid dimensions
    grid_size = 20
    grid_step = 1  # <-- FIXED: was 1.0 (float), now int

    # Main loop
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # delta time in seconds (not strictly needed with fixed step)
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False

        # ---------- Input ----------
        keys = pygame.key.get_pressed()
        move_dir = [0, 0, 0]  # x, y, z movement (world axes)

        # Forward/backward relative to player angle
        if keys[K_UP] or keys[K_w]:
            move_dir[0] -= MOVE_SPEED * math.sin(player_angle)
            move_dir[2] -= MOVE_SPEED * math.cos(player_angle)
        if keys[K_DOWN] or keys[K_s]:
            move_dir[0] += MOVE_SPEED * math.sin(player_angle)
            move_dir[2] += MOVE_SPEED * math.cos(player_angle)
        # Strafe left/right (perpendicular)
        if keys[K_LEFT] or keys[K_a]:
            move_dir[0] -= MOVE_SPEED * math.sin(player_angle + math.pi/2)
            move_dir[2] -= MOVE_SPEED * math.cos(player_angle + math.pi/2)
        if keys[K_RIGHT] or keys[K_d]:
            move_dir[0] -= MOVE_SPEED * math.sin(player_angle - math.pi/2)
            move_dir[2] -= MOVE_SPEED * math.cos(player_angle - math.pi/2)

        # Rotation
        if keys[K_q]:
            player_angle += ROT_SPEED
        if keys[K_e]:
            player_angle -= ROT_SPEED

        # Update player position with collision
        new_pos = vec_add(player.position, move_dir)
        if not check_collision(new_pos, castle_objects):
            player.move_to(new_pos)

        # ---------- Camera ----------
        # Camera follows behind player
        cam_offset = (CAMERA_DISTANCE * math.sin(player_angle),
                      CAMERA_HEIGHT,
                      CAMERA_DISTANCE * math.cos(player_angle))
        cam_pos = vec_sub(player.position, cam_offset)  # behind player
        target = player.position  # look at player
        view = look_at(cam_pos, target)

        # ---------- Prepare scene ----------
        # Collect all objects to render (castle + player)
        render_objects = castle_objects + [player]

        # For each object, transform vertices to camera space and project
        # Also collect faces with their projected points and depth
        faces_to_draw = []  # each: (depth, color, projected_points)
        for obj in render_objects:
            # Transform all vertices of this object to camera space
            cam_verts = []
            for v in obj.vertices:
                cam_verts.append(world_to_camera(v, view))

            # Process each face
            for face_idx, face in enumerate(obj.faces):
                # Project each vertex in face
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
                # Average depth for sorting
                depth = depth_sum / len(face)
                faces_to_draw.append((depth, obj.colors[face_idx], proj_points))

        # Sort faces back-to-front (painter's algorithm)
        faces_to_draw.sort(key=lambda x: x[0], reverse=True)

        # ---------- Render ----------
        screen.fill(SKY_COLOR)

        # Draw ground grid (in world space, but we need to project it)
        # We'll do a simple grid of lines on y=0 plane
        for i in range(-grid_size, grid_size+1, grid_step):
            # Line along X at constant Z
            p1 = world_to_camera((i, 0, -grid_size), view)
            p2 = world_to_camera((i, 0, grid_size), view)
            # Project both
            sp1 = project(p1)
            sp2 = project(p2)
            if sp1 and sp2:
                pygame.draw.line(screen, (100,100,100), sp1, sp2, 1)
            # Line along Z at constant X
            p1 = world_to_camera((-grid_size, 0, i), view)
            p2 = world_to_camera((grid_size, 0, i), view)
            sp1 = project(p1)
            sp2 = project(p2)
            if sp1 and sp2:
                pygame.draw.line(screen, (100,100,100), sp1, sp2, 1)

        # Draw all faces
        for depth, color, points in faces_to_draw:
            if len(points) >= 3:
                pygame.draw.polygon(screen, color, points)
                # Optional wireframe
                pygame.draw.polygon(screen, WIREFRAME_COLOR, points, 1)

        # Update display
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
