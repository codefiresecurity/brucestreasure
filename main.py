import pygame
import random
import math
import os
import sys
from collections import deque

# ==========================================================
# CONFIG
# ==========================================================

SCREEN_WIDTH = 1870
SCREEN_HEIGHT = 920
TILE_SIZE = 32

VISIBLE_COLS = SCREEN_WIDTH // TILE_SIZE
VISIBLE_ROWS = SCREEN_HEIGHT // TILE_SIZE

WORLD_COLS = 120
WORLD_ROWS = 120

FPS = 60

FLOOR = 0
WALL = 1
SPIKE = 2
GOAL = 9

ASSET_PATH = "assets"
DEBUG = False

MIN_PATH_WIDTH = 2
SPIKE_PROFUSION = 0.07  # 0.05=scarce, 0.20=spiky 

# Colors for summary
COLOR_GOLD = (255, 215, 0)
COLOR_SUN = (255, 223, 0)
COLOR_SUN_GLOW = (255, 255, 100)
COLOR_GREEN = (0, 255, 100)
COLOR_BLUE = (100, 200, 255)
COLOR_PURPLE = (200, 100, 255)
COLOR_RED = (255, 100, 100)

# ==========================================================
# INIT
# ==========================================================

pygame.init()
pygame.mixer.init()
#screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("BRUCE'S Treasure")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 24)
big_font = pygame.font.SysFont("consolas", 48)
huge_font = pygame.font.SysFont("consolas", 72)

# ==========================================================
# AUDIO
# ==========================================================

def load_sound(name):
    path = os.path.join(ASSET_PATH, name)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None

if os.path.exists(os.path.join(ASSET_PATH, "music.mp3")):
    pygame.mixer.music.load(os.path.join(ASSET_PATH, "music.mp3"))
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)

SND_SPIKE = load_sound("hit.wav")
SND_PICKUP = load_sound("coin.wav")
SND_EXTEND = load_sound("spike_extend.wav") or SND_SPIKE
SND_WIN = load_sound("win.wav") or SND_PICKUP

# ==========================================================
# SPRITES
# ==========================================================

def load_sprite(name):
    path = os.path.join(ASSET_PATH, name)
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
    return None

SPRITES = {
    FLOOR: load_sprite("floor.png"),
    WALL: load_sprite("wall.png"),
    SPIKE: load_sprite("spike.png"),
    GOAL: load_sprite("sun.png")
}

PLAYER_SPRITE = load_sprite("player.png")

# ==========================================================
# PARTICLE SYSTEM
# ==========================================================

class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def add_burst(self, x, y, color=(255, 255, 100), count=8):
        for _ in range(count):
            self.particles.append({
                "x": x, "y": y,
                "vx": random.uniform(-80, 80),
                "vy": random.uniform(-80, 80),
                "life": 1.0,
                "color": color,
                "size": random.uniform(2, 6)
            })
    
    def update(self, delta_time):
        for p in self.particles[:]:
            p["x"] += p["vx"] * delta_time
            p["y"] += p["vy"] * delta_time
            p["vy"] += 300 * delta_time
            p["life"] -= delta_time * 3
            if p["life"] <= 0:
                self.particles.remove(p)
    
    def draw(self, cam_x, cam_y):
        for p in self.particles:
            alpha = int(255 * p["life"])
            size = int(p["size"] * p["life"])
            if size > 0:
                color = (*p["color"], alpha)
                surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                px = int(p["x"] - cam_x)
                py = int(p["y"] - cam_y)
                screen.blit(surf, (px-size, py-size))

# ==========================================================
# ITEM SYSTEM
# ==========================================================

ITEM_TYPES = {
    3: {"name":"Coin","points":10,"spawn":0.02,"sprite":"coin.png"},
    4: {"name":"Mushroom","points":25,"spawn":0.01,"sprite":"mushroom.png"},
    6: {"name":"Trophy","points":100,"spawn":0.005,"sprite":"trophy.png"},
    7: {"name":"Poison","points":-100,"spawn":0.01,"sprite":"poison.png"},
}

def draw_stats_bar():
    if player is None:
        return  # Safe during splash / init phases

    bar_height = 50
    bar_surf = pygame.Surface((SCREEN_WIDTH, bar_height), pygame.SRCALPHA)
    bar_surf.fill((0, 0, 0, 160))  # semi-transparent dark background

    padding = 20
    icon_size = 32
    icon_padding = 8
    count_padding = 6

    # Left: Level
    level_text = font.render(f"Level {player.level}", True, (220, 220, 255))
    bar_surf.blit(level_text, (padding, (bar_height - level_text.get_height()) // 2))

    # Right: Score
    score_text = font.render(f"Score: {player.score:,}", True, COLOR_GOLD)
    score_x = SCREEN_WIDTH - score_text.get_width() - padding
    bar_surf.blit(score_text, (score_x, (bar_height - score_text.get_height()) // 2))

    # Center: Collected items (icons + counts)
    items_to_show = [(tid, cnt) for tid, cnt in player.collected.items() if cnt > 0 or tid == 3]
    if items_to_show:
        total_width = len(items_to_show) * (icon_size + count_padding + 40)  # rough estimate
        start_x = (SCREEN_WIDTH - total_width) // 2

        for i, (tile_id, count) in enumerate(items_to_show):
            x_pos = start_x + i * (icon_size + 48)  # 48 = icon + spacing

            # Icon
            if tile_id in ITEM_TYPES and ITEM_TYPES[tile_id].get("image"):
                icon = ITEM_TYPES[tile_id]["image"]
                icon = pygame.transform.scale(icon, (icon_size, icon_size))
                bar_surf.blit(icon, (x_pos, (bar_height - icon_size) // 2))

            # Count (right of icon)
            count_str = f"×{count}" if count > 0 else "0"
            count_color = COLOR_RED if tile_id == 7 else (255, 255, 220)
            count_text = font.render(count_str, True, count_color)
            bar_surf.blit(count_text, (x_pos + icon_size + count_padding,
                                       (bar_height - count_text.get_height()) // 2 + 2))

    # Final blit to screen
    screen.blit(bar_surf, (0, 0))

for tile,data in ITEM_TYPES.items():
    data["image"] = load_sprite(data["sprite"])

# ==========================================================
# DUNGEON GENERATOR
# ==========================================================

def generate_world():
    grid = [[WALL for _ in range(WORLD_COLS)] for _ in range(WORLD_ROWS)]
    rooms = []

    for _ in range(12):
        w = random.randint(8,15)
        h = random.randint(8,15)
        x = random.randint(3,WORLD_COLS-w-3)
        y = random.randint(3,WORLD_ROWS-h-3)

        new_room = pygame.Rect(x,y,w,h)
        failed = False
        for other in rooms:
            if new_room.colliderect(other.inflate(-MIN_PATH_WIDTH*2, -MIN_PATH_WIDTH*2)):
                failed = True
                break

        if not failed:
            for i in range(x+1,x+w-1):
                for j in range(y+1,y+h-1):
                    grid[j][i] = FLOOR
            rooms.append(new_room)

    for i in range(1,len(rooms)):
        room1 = rooms[i-1]
        room2 = rooms[i]
        door1_x = random.randint(room1.left+2, room1.right-3)
        door1_y = random.choice([room1.top+2, room1.bottom-3]) if random.random() < 0.5 else random.randint(room1.top+2, room1.bottom-3)
        door2_x = random.randint(room2.left+2, room2.right-3)
        door2_y = random.choice([room2.top+2, room2.bottom-3]) if random.random() < 0.5 else random.randint(room2.top+2, room2.bottom-3)
        
        if abs(door1_x - door2_x) > abs(door1_y - door2_y):
            for x in range(min(door1_x, door2_x)-1, max(door1_x, door2_x)+2):
                for lane in [0, 1]:
                    grid[int(door1_y + lane)][int(x)] = FLOOR
                    grid[int(door2_y + lane)][int(x)] = FLOOR
            for y in range(min(door1_y, door2_y), max(door1_y, door2_y)+1):
                grid[int(y)][int(door1_x)] = FLOOR
                grid[int(y)][int(door2_x)] = FLOOR
        else:
            for y in range(min(door1_y, door2_y)-1, max(door1_y, door2_y)+2):
                for lane in [0, 1]:
                    grid[int(y)][int(door1_x + lane)] = FLOOR
                    grid[int(y)][int(door2_x + lane)] = FLOOR
            for x in range(min(door1_x, door2_x), max(door1_x, door2_x)+1):
                grid[int(door1_y)][int(x)] = FLOOR
                grid[int(door2_y)][int(x)] = FLOOR

    if rooms:
        gx,gy = rooms[-1].center
        for dy in range(-3,4):
            for dx in range(-3,4):
                nx, ny = int(gx+dx), int(gy+dy)
                if 0 <= nx < WORLD_COLS and 0 <= ny < WORLD_ROWS and grid[ny][nx] == FLOOR:
                    grid[ny][nx] = GOAL
                    break

    return grid, rooms[0].center if rooms else (5, 5)

# ==========================================================
# ITEM PLACEMENT (this was missing in the last version)
# ==========================================================

def place_items(grid):
    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] == FLOOR:
                # Avoid placing near spikes or goal
                too_close = False
                for dx, dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < WORLD_COLS and 0 <= ny < WORLD_ROWS:
                        if grid[ny][nx] in (SPIKE, GOAL):
                            too_close = True
                            break
                if too_close:
                    continue

                r = random.random()
                cumulative = 0.0
                for tid, data in sorted(ITEM_TYPES.items(), key=lambda item: item[1]["spawn"]):
                    cumulative += data["spawn"]
                    if r < cumulative:
                        grid[y][x] = tid
                        break

# ==========================================================
# SPIKE SYSTEM
# ==========================================================

class SpikeSystem:
    def __init__(self):
        self.spikes = {}
    
    def generate_spikes(self, grid):
        self.spikes.clear()
        dirs = [(0,-1,"BOTTOM"), (0,1,"TOP"), (-1,0,"RIGHT"), (1,0,"LEFT")]
        
        for y in range(1, WORLD_ROWS-1):
            for x in range(1, WORLD_COLS-1):
                if grid[y][x] == FLOOR:
                    for dx, dy, direction in dirs:
                        sx, sy = x + dx, y + dy
                        if (0 <= sx < WORLD_COLS and 0 <= sy < WORLD_ROWS and 
                            grid[sy][sx] == WALL and random.random() < SPIKE_PROFUSION):
                            
                            key = (x, y, direction)
                            self.spikes[key] = {
                                "origin": (sx, sy),
                                "target": (x, y),
                                "dir": direction,
                                "phase": random.random() * math.tau,
                                "extend_progress": 0.0,
                                "played_sound": False
                            }
    
    def update(self, delta_time, player_x, player_y, particles):
        hit = False
        for key, spike in self.spikes.items():
            target_x, target_y = spike["target"]
            spike["phase"] += delta_time * 3
            target_active = math.sin(spike["phase"]) > 0
            
            extend_speed = 5 if target_active else 2.5
            if target_active and spike["extend_progress"] < 1.0:
                spike["extend_progress"] = min(1.0, spike["extend_progress"] + delta_time * extend_speed)
                if spike["extend_progress"] > 0.3 and not spike["played_sound"]:
                    if SND_EXTEND: SND_EXTEND.play()
                    spike["played_sound"] = True
            elif not target_active and spike["extend_progress"] > 0.0:
                spike["extend_progress"] = max(0.0, spike["extend_progress"] - delta_time * extend_speed)
                spike["played_sound"] = False
            
            if (spike["extend_progress"] >= 0.95 and target_x == player_x and target_y == player_y):
                hit = True
                particles.add_burst(
                    player_x * TILE_SIZE + TILE_SIZE//2,
                    player_y * TILE_SIZE + TILE_SIZE//2,
                    color=(255, 100, 100)
                )
        
        return hit
    
    def draw_spike(self, spike, cam_x, cam_y):
        progress = spike["extend_progress"]
        if progress <= 0.01:
            return
        
        ox = spike["origin"][0] * TILE_SIZE - cam_x + TILE_SIZE // 2
        oy = spike["origin"][1] * TILE_SIZE - cam_y + TILE_SIZE // 2
        tx = spike["target"][0] * TILE_SIZE - cam_x + TILE_SIZE // 2
        ty = spike["target"][1] * TILE_SIZE - cam_y + TILE_SIZE // 2
        
        dx, dy = tx - ox, ty - oy
        current_x = ox + dx * progress
        current_y = oy + dy * progress
        
        angle_map = {
            "BOTTOM": 0, "TOP": 180, "RIGHT": 90, "LEFT": -90
        }
        angle_deg = angle_map[spike["dir"]]
        
        scale = 0.7 + progress * 0.5
        scaled_size = int(TILE_SIZE * scale)
        scaled = pygame.transform.scale(SPRITES[SPIKE], (scaled_size, scaled_size))
        rotated = pygame.transform.rotate(scaled, angle_deg)
        rect = rotated.get_rect(center=(current_x, current_y))
        screen.blit(rotated, rect)

# ==========================================================
# PLAYER
# ==========================================================

class Player:
    def __init__(self, start):
        self.x, self.y = int(start[0]), int(start[1])
        self.score = 0
        self.dead = False
        self.move_delay = 140
        self.last_move_time = 0
        self.level = 1
        
        # New: item collection counters
        self.collected = {
            3: 0,   # Coin
            4: 0,   # Mushroom
            6: 0,   # Trophy
            7: 0    # Poison
        }

    def move(self, dx, dy, grid):
        now = pygame.time.get_ticks()
        if now - self.last_move_time < self.move_delay:
            return
        if dx == 0 and dy == 0:
            return

        self.last_move_time = now
        nx = max(0, min(WORLD_COLS-1, self.x + dx))
        ny = max(0, min(WORLD_ROWS-1, self.y + dy))

        tile = grid[ny][nx]
        if tile == WALL:
            return

        if tile in ITEM_TYPES:
            self.score += ITEM_TYPES[tile]["points"]
            self.collected[tile] += 1              # ← increment counter
            if SND_PICKUP: SND_PICKUP.play()
            grid[ny][nx] = FLOOR

        if tile == GOAL:
            return "NEXT"

        self.x, self.y = nx, ny

# ==========================================================
# UTILITIES
# ==========================================================

camera_x = 0
camera_y = 0

def get_camera(player):
    global camera_x, camera_y
    target_x = player.x*TILE_SIZE - SCREEN_WIDTH//2
    target_y = player.y*TILE_SIZE - SCREEN_HEIGHT//2
    camera_x += (target_x - camera_x) * 0.12
    camera_y += (target_y - camera_y) * 0.12
    return int(camera_x), int(camera_y)

def load_scores():
    if not os.path.exists("highscores.txt"):
        return []
    with open("highscores.txt") as f:
        return [int(x.strip()) for x in f]

def save_score(score):
    scores = load_scores()
    scores.append(score)
    scores = sorted(scores,reverse=True)[:5]
    with open("highscores.txt","w") as f:
        for s in scores:
            f.write(str(s)+"\n")

def draw_torch(player):
    darkness = pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
    darkness.fill((0,0,0,220))
    pygame.draw.circle(darkness,(0,0,0,0),(SCREEN_WIDTH//2,SCREEN_HEIGHT//2),200)
    screen.blit(darkness,(0,0))

def draw_minimap(grid,player):
    mini = pygame.Surface((200,200))
    mini.fill((20,20,20))
    scale = 200/WORLD_COLS
    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] == FLOOR:
                pygame.draw.rect(mini,(90,90,90),(x*scale,y*scale,2,2))
    pygame.draw.rect(mini,(255,0,0),(player.x*scale,player.y*scale,4,4))
    screen.blit(mini,(SCREEN_WIDTH-210,10))

# ==========================================================
# LEVEL SUMMARY SCREEN
# ==========================================================

def draw_level_summary(level, score_gained, total_score):
    screen.fill((5, 5, 20))  # Dark blue background
    
    # RAINBOW BACKGROUND GRADIENT
    for i in range(SCREEN_HEIGHT):
        t = i / SCREEN_HEIGHT
        r = int(50 + 200 * math.sin(t * math.tau + 0))
        g = int(50 + 200 * math.sin(t * math.tau + math.tau/3))
        b = int(50 + 200 * math.sin(t * math.tau + math.tau*2/3))
        pygame.draw.line(screen, (r,g,b), (0,i), (SCREEN_WIDTH,i))
    
    # MASSIVE "LEVEL COMPLETE!"
    title = huge_font.render("LEVEL COMPLETE!", True, COLOR_GOLD)
    title_glow = huge_font.render("LEVEL COMPLETE!", True, COLOR_SUN_GLOW)
    screen.blit(title_glow, (SCREEN_WIDTH//2 - title_glow.get_width()//2 + 2, 140))
    screen.blit(title_glow, (SCREEN_WIDTH//2 - title_glow.get_width()//2 - 2, 140))
    screen.blit(title_glow, (SCREEN_WIDTH//2 - title_glow.get_width()//2, 142))
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 140))
    
    # Level info with colors
    lvl_text = font.render(f"🏆  Level {level-1} Conquered!  🏆", True, COLOR_GREEN)
    gain_text = font.render(f"💰  Score Gained: +{score_gained:,}  💰", True, COLOR_GOLD)
    total_text = font.render(f"⭐  Total Score: {total_score:,}  ⭐", True, COLOR_PURPLE)
    
    screen.blit(lvl_text, (SCREEN_WIDTH//2 - lvl_text.get_width()//2, 280))
    screen.blit(gain_text, (SCREEN_WIDTH//2 - gain_text.get_width()//2, 330))
    screen.blit(total_text, (SCREEN_WIDTH//2 - total_text.get_width()//2, 380))
    
    # GIANT ANIMATED SUN
    sun_center = (SCREEN_WIDTH//2, 500)
    sun_rect = pygame.Rect(0,0,140,140)
    sun_rect.center = sun_center
    
    # Pulsing glow rings
    for ring in range(4):
        glow_size = 70 + ring * 15 + math.sin(pygame.time.get_ticks() * 0.01 + ring) * 10
        glow_alpha = 100 - ring * 20
        glow_surf = pygame.Surface((glow_size*2, glow_size*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*COLOR_SUN_GLOW, glow_alpha), (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (sun_center[0]-glow_size, sun_center[1]-glow_size))
    
    # Main sun
    pygame.draw.circle(screen, COLOR_SUN, sun_center, 65)
    pygame.draw.circle(screen, (255, 255, 150), sun_center, 55)
    pygame.draw.circle(screen, COLOR_SUN, sun_center, 45)
    
    # Sun rays
    for i in range(16):
        angle = i * math.tau / 16
        end_x = sun_center[0] + math.cos(angle) * 85
        end_y = sun_center[1] + math.sin(angle) * 85
        pygame.draw.line(screen, COLOR_SUN_GLOW, sun_center, (end_x, end_y), 8)
    
    # Prompt
    prompt = font.render("🎮  Press ANY KEY for Next Challenge  🎮", True, COLOR_BLUE)
    screen.blit(prompt, (SCREEN_WIDTH//2 - prompt.get_width()//2, 670))

# ==========================================================
# GAME STATES
# ==========================================================

STATE_SPLASH = 0
STATE_PLAY = 1
STATE_SUMMARY = 2
STATE_GAMEOVER = 3

state = STATE_SPLASH
grid = None
player = None
spike_system = SpikeSystem()
particles = ParticleSystem()
last_time = pygame.time.get_ticks()
last_level_score = 0

# ==========================================================
# SPLASH SCREEN
# ==========================================================

def draw_splash():
    screen.fill((0,0,0))
    ascii_title = [
        "  ██████╗ ██████╗ ██╗   ██╗ ██████╗███████╗",
        "  ██╔══██╗██╔══██╗██║   ██║██╔════╝██╔════╝",
        "  ██████╔╝██████╔╝██║   ██║██║     █████╗  ",
        "  ██╔══██╗██╔══██╗██║   ██║██║     ██╔══╝  ",
        "  ██████╔╝██║  ██║╚██████╔╝╚██████╗███████╗",
        "  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝",
        "",
        "                   v1.0",
        "",
        "             BRUCE'S TREASURE",
        "",
        "         > PRESS ANY KEY TO BEGIN <",
    ]
    y_offset = 160
    for line in ascii_title:
        text = font.render(line, True, (0,255,0))
        rect = text.get_rect(center=(SCREEN_WIDTH//2, y_offset))
        screen.blit(text, rect)
        y_offset += 35

# ==========================================================
# MAIN LOOP
# ==========================================================

while True:
    clock.tick(FPS)
    current_time = pygame.time.get_ticks()
    delta_time = (current_time - last_time) / 1000.0
    last_time = current_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            
            if state == STATE_SPLASH:
                grid, start = generate_world()
                place_items(grid)               # ← restored
                player = Player(start)
                player.level = 1
                spike_system.generate_spikes(grid)
                last_level_score = 0
                state = STATE_PLAY
            elif state == STATE_SUMMARY:
                grid, start = generate_world()
                place_items(grid)               # ← restored
                player.level += 1
                spike_system.generate_spikes(grid)
                particles.particles.clear()
                last_level_score = player.score
                state = STATE_PLAY

    if state == STATE_SPLASH:
        draw_splash()        
        pygame.display.flip()
        continue

    elif state == STATE_PLAY:
        particles.update(delta_time)
        player.dead = spike_system.update(delta_time, player.x, player.y, particles)

        keys = pygame.key.get_pressed()
        dx=dy=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx=-1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy=-1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy=1

        result = player.move(dx,dy,grid)

        if player.dead:
            if SND_SPIKE: SND_SPIKE.play()
            save_score(player.score)
            state = STATE_GAMEOVER
            continue

        if result == "NEXT":
            if SND_WIN: SND_WIN.play()
            state = STATE_SUMMARY
            continue

        # In STATE_PLAY drawing section:
        cam_x, cam_y = get_camera(player)
        screen.fill((0, 0, 0))

        for y in range(WORLD_ROWS):
            for x in range(WORLD_COLS):
                rect = pygame.Rect(x * TILE_SIZE - cam_x, y * TILE_SIZE - cam_y, TILE_SIZE, TILE_SIZE)
                if not rect.colliderect(screen.get_rect()):
                    continue

                tile = grid[y][x]

                # Floor base layer
                if tile == FLOOR or tile in ITEM_TYPES or tile == GOAL:
                    if SPRITES.get(FLOOR):
                        screen.blit(SPRITES[FLOOR], rect)
                    else:
                        pygame.draw.rect(screen, (90, 90, 110), rect)   # slightly darker for contrast

                # Items / collectibles
                if tile in ITEM_TYPES and ITEM_TYPES[tile].get("image"):
                    img = ITEM_TYPES[tile]["image"]
                    # Optional: make semi-transparent
                    # img.set_alpha(220)  # uncomment if you want subtle floor visibility through item
                    screen.blit(img, rect)

                # Goal (sun)
                elif tile == GOAL and SPRITES.get(GOAL):
                    screen.blit(SPRITES[GOAL], rect)

        # Spikes are drawn later (on top of everything)
        for spike in spike_system.spikes.values():
            spike_system.draw_spike(spike, cam_x, cam_y)

        # Player on top of everything
        px = player.x * TILE_SIZE - cam_x
        py = player.y * TILE_SIZE - cam_y
        if PLAYER_SPRITE:
            screen.blit(PLAYER_SPRITE, (px, py))
        else:
            pygame.draw.rect(screen, (0, 120, 255), (px, py, TILE_SIZE, TILE_SIZE))
        particles.draw(cam_x, cam_y)
        draw_torch(player)
        draw_minimap(grid, player)
        
        # Level & Score UI
        #ui_text = font.render(f"Level: {player.level}  Score: {player.score:,}", True, (255,255,255))
        #screen.blit(ui_text, (10,10))
        draw_stats_bar()
        pygame.display.flip()

    elif state == STATE_SUMMARY:
        draw_level_summary(player.level, player.score - last_level_score, player.score)
        pygame.display.flip()
        continue

    elif state == STATE_GAMEOVER:
        screen.fill((0,0,0))
        over = big_font.render("GAME OVER", True, COLOR_RED)
        screen.blit(over, (SCREEN_WIDTH//2 - over.get_width()//2, 250))

        scores = load_scores()
        y = 350
        title_hs = font.render("HIGH SCORES", True, COLOR_GOLD)
        screen.blit(title_hs, (SCREEN_WIDTH//2 - title_hs.get_width()//2, y))
        y += 50
        
        for i, s in enumerate(scores):
            hs_text = font.render(f"{i+1}. {s:,}", True, COLOR_SUN_GLOW)
            screen.blit(hs_text, (SCREEN_WIDTH//2 - hs_text.get_width()//2, y))
            y += 35

        restart = font.render("Press ESC to Quit | Any Key to Restart", True, COLOR_BLUE)
        screen.blit(restart, (SCREEN_WIDTH//2 - restart.get_width()//2, 600))

        pygame.display.flip()
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RETURN] or keys[pygame.K_SPACE]:
            state = STATE_SPLASH

# Clean exit
pygame.quit()
sys.exit()