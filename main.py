import pygame
import random
import math
import os
import sys
import json
from collections import deque

# ==========================================================
# CONFIG
# ==========================================================

TILE_SIZE = 32

WORLD_COLS = 120
WORLD_ROWS = 120

FPS = 60

FLOOR = 0
WALL = 1
SPIKE = 2
TRAP = 10  # Trap/hole - can be stepped on, but kills the player
GOAL = 9

ASSET_PATH = "assets"
DEBUG = False

MIN_PATH_WIDTH = 2
SPIKE_PROFUSION = 0.07  # 0.05=scarce, 0.20=spiky
TRAP_PROFUSION = 0.08  # 0.05=few traps, 0.15=many traps (creates maze-like paths)
SPIKE_DAMAGE = 20  # Damage taken when hit by a spike
EXTRA_LIFE_THRESHOLD = 250000  # Points needed for extra life
FIREBALL_PROFUSION = 0.03  # 0.01=rare, 0.10=common
FIREBALL_DAMAGE = 25  # Damage taken when hit by fireball
FIREBALL_SPEED = 3  # Speed of fireballs

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
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()

VISIBLE_COLS = SCREEN_WIDTH // TILE_SIZE
VISIBLE_ROWS = SCREEN_HEIGHT // TILE_SIZE

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

MUSIC_PLAYLIST = ["music.mp3", "01.ogg", "02.ogg", "03.ogg", "04.ogg", "05.ogg", "06.ogg", "07.ogg", "08.ogg"]
SONG_FINISHED = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(SONG_FINISHED)

def play_next_song():
    if MUSIC_PLAYLIST:
        next_song = random.choice(MUSIC_PLAYLIST)
        if os.path.exists(os.path.join(ASSET_PATH, next_song)):
            pygame.mixer.music.load(os.path.join(ASSET_PATH, next_song))
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play()
        else:
            print(f"Warning: {next_song} not found in assets.")
    else:
        print("No songs in playlist.")

play_next_song()

SND_SPIKE = load_sound("hit.wav")
SND_PICKUP = load_sound("coin.wav")
SND_EXTEND = load_sound("spike_extend.wav") or SND_SPIKE
SND_WIN = load_sound("win.wav") or SND_PICKUP
SND_TRAP_FALL = load_sound("trap_fall.wav") or SND_SPIKE
SND_EXTRA_LIFE = load_sound("extra_life.mp3")
SND_FALL = load_sound("fall.mp3")
SND_SPIKE_HIT = load_sound("spikehit.mp3")

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
    GOAL: load_sprite("sun.png"),
    TRAP: load_sprite("floor.png"),
    "FIREBALL": load_sprite("fireball.png")
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
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                px = int(p["x"] - cam_x)
                py = int(p["y"] - cam_y)
                screen.blit(surf, (px - size, py - size))

# ==========================================================
# ITEM SYSTEM
# ==========================================================

ITEM_TYPES = {
    3: {"name": "Coin", "points": 10, "spawn": 0.02, "sprite": "coin.png"},
    4: {"name": "Mushroom", "points": 25, "spawn": 0.01, "sprite": "mushroom.png"},
    6: {"name": "Trophy", "points": 100, "spawn": 0.005, "sprite": "trophy.png"},
    7: {"name": "Poison", "points": -100, "spawn": 0.01, "sprite": "poison.png"},
    8: {"name": "Coins", "points": 200, "spawn": 0.002, "sprite": "coins.png"},
    90: {"name": "Medium Yellow Gem", "points": 10000, "spawn": 0.002, "sprite": "gem10k.png"},
    100: {"name": "Big Yellow Gem", "points": 100000, "spawn": 0.002, "sprite": "gem100k.png"},
    110: {"name": "Purple Gem", "points": 80000, "spawn": 0.002, "sprite": "gem80ka.png"},
    120: {"name": "Blue Gem", "points": 80000, "spawn": 0.002, "sprite": "gem80kb.png"},
    130: {"name": "Green Gem", "points": 80000, "spawn": 0.002, "sprite": "gem80kc.png"}
}

def draw_stats_bar():
    if player is None:
        return

    bar_height = 50
    bar_surf = pygame.Surface((SCREEN_WIDTH, bar_height), pygame.SRCALPHA)
    bar_surf.fill((0, 0, 0, 160))

    padding = 20
    icon_size = 32
    count_padding = 6

    level_text = font.render(f"Level {player.level}", True, (220, 220, 255))
    bar_surf.blit(level_text, (padding, (bar_height - level_text.get_height()) // 2))

    # Draw lives (hearts)
    lives_text = font.render(f"Lives: {player.lives}", True, COLOR_RED)
    bar_surf.blit(lives_text, (padding + 100, (bar_height - lives_text.get_height()) // 2))

    # Draw health
    health_text = font.render(f"Health: {player.health}", True, COLOR_GREEN)
    bar_surf.blit(health_text, (padding + 220, (bar_height - health_text.get_height()) // 2))

    score_text = font.render(f"Score: {player.score:,}", True, COLOR_GOLD)
    score_x = SCREEN_WIDTH - score_text.get_width() - padding
    bar_surf.blit(score_text, (score_x, (bar_height - score_text.get_height()) // 2))

    items_to_show = [(tid, cnt) for tid, cnt in player.collected.items() if cnt > 0 or tid == 3]
    if items_to_show:
        total_width = len(items_to_show) * (icon_size + count_padding + 40)
        start_x = (SCREEN_WIDTH - total_width) // 2

        for i, (tile_id, count) in enumerate(items_to_show):
            x_pos = start_x + i * (icon_size + 48)

            if tile_id in ITEM_TYPES and ITEM_TYPES[tile_id].get("image"):
                icon = ITEM_TYPES[tile_id]["image"]
                icon = pygame.transform.scale(icon, (icon_size, icon_size))
                bar_surf.blit(icon, (x_pos, (bar_height - icon_size) // 2))

            count_str = f"×{count}" if count > 0 else "0"
            count_color = COLOR_RED if tile_id == 7 else (255, 255, 220)
            count_text = font.render(count_str, True, count_color)
            bar_surf.blit(count_text, (x_pos + icon_size + count_padding,
                                       (bar_height - count_text.get_height()) // 2 + 2))

    screen.blit(bar_surf, (0, 0))

for tile, data in ITEM_TYPES.items():
    data["image"] = load_sprite(data["sprite"])

if SPRITES.get(TRAP):
    trap_img = SPRITES[TRAP]
    darkTrap = pygame.Surface((trap_img.get_width(), trap_img.get_height()), pygame.SRCALPHA)
    for x in range(trap_img.get_width()):
        for y in range(trap_img.get_height()):
            pixel = trap_img.get_at((x, y))
            if pixel.a > 0:
                darkTrap.set_at(
                    (x, y),
                    (max(0, pixel[0] - 50), max(0, pixel[1] - 50), max(0, pixel[2] - 50), pixel[3])
                )
    SPRITES[TRAP] = darkTrap

# ==========================================================
# DUNGEON GENERATOR
# ==========================================================

def generate_world():
    grid = [[WALL for _ in range(WORLD_COLS)] for _ in range(WORLD_ROWS)]
    rooms = []

    for _ in range(12):
        w = random.randint(8, 15)
        h = random.randint(8, 15)
        x = random.randint(3, WORLD_COLS - w - 3)
        y = random.randint(3, WORLD_ROWS - h - 3)

        new_room = pygame.Rect(x, y, w, h)
        failed = False
        for other in rooms:
            if new_room.colliderect(other.inflate(-MIN_PATH_WIDTH * 2, -MIN_PATH_WIDTH * 2)):
                failed = True
                break

        if not failed:
            for i in range(x + 1, x + w - 1):
                for j in range(y + 1, y + h - 1):
                    grid[j][i] = FLOOR
            rooms.append(new_room)

    for i in range(1, len(rooms)):
        room1 = rooms[i - 1]
        room2 = rooms[i]
        door1_x = random.randint(room1.left + 2, room1.right - 3)
        door1_y = random.choice([room1.top + 2, room1.bottom - 3]) if random.random() < 0.5 else random.randint(room1.top + 2, room1.bottom - 3)
        door2_x = random.randint(room2.left + 2, room2.right - 3)
        door2_y = random.choice([room2.top + 2, room2.bottom - 3]) if random.random() < 0.5 else random.randint(room2.top + 2, room2.bottom - 3)

        if abs(door1_x - door2_x) > abs(door1_y - door2_y):
            for x in range(min(door1_x, door2_x) - 1, max(door1_x, door2_x) + 2):
                for lane in [0, 1]:
                    grid[int(door1_y + lane)][int(x)] = FLOOR
                    grid[int(door2_y + lane)][int(x)] = FLOOR
            for y in range(min(door1_y, door2_y), max(door1_y, door2_y) + 1):
                grid[int(y)][int(door1_x)] = FLOOR
                grid[int(y)][int(door2_x)] = FLOOR
        else:
            for y in range(min(door1_y, door2_y) - 1, max(door1_y, door2_y) + 2):
                for lane in [0, 1]:
                    grid[int(y)][int(door1_x + lane)] = FLOOR
                    grid[int(y)][int(door2_x + lane)] = FLOOR
            for x in range(min(door1_x, door2_x), max(door1_x, door2_x) + 1):
                grid[int(door1_y)][int(x)] = FLOOR
                grid[int(door2_y)][int(x)] = FLOOR

    if rooms:
        gx, gy = rooms[-1].center
        placed_goal = False
        for dy in range(-3, 4):
            if placed_goal:
                break
            for dx in range(-3, 4):
                nx, ny = int(gx + dx), int(gy + dy)
                if 0 <= nx < WORLD_COLS and 0 <= ny < WORLD_ROWS and grid[ny][nx] == FLOOR:
                    grid[ny][nx] = GOAL
                    placed_goal = True
                    break

    return grid, rooms[0].center if rooms else (5, 5)

# ==========================================================
# ITEM PLACEMENT
# ==========================================================

def place_items(grid):
    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] == FLOOR:
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
# TRAP SYSTEM
# ==========================================================

def place_traps(grid, start_pos, goal_pos):
    safe_radius = 8

    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] != FLOOR:
                continue

            start_dist = abs(x - start_pos[0]) + abs(y - start_pos[1])
            if start_dist < safe_radius:
                continue

            goal_dist = abs(x - goal_pos[0]) + abs(y - goal_pos[1])
            if goal_dist < safe_radius:
                continue

            too_close_to_spike = False
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < WORLD_COLS and 0 <= ny < WORLD_ROWS:
                        if grid[ny][nx] == SPIKE:
                            too_close_to_spike = True
                            break
                if too_close_to_spike:
                    break
            if too_close_to_spike:
                continue

            if would_trap_create_dead_end(grid, x, y):
                continue

            if random.random() < TRAP_PROFUSION:
                grid[y][x] = TRAP

def would_trap_create_dead_end(grid, x, y):
    floor_count = 0
    for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < WORLD_COLS and 0 <= ny < WORLD_ROWS:
            if grid[ny][nx] in (FLOOR, GOAL):
                floor_count += 1
    return floor_count < 2

# ==========================================================
# SPIKE SYSTEM
# ==========================================================

class SpikeSystem:
    def __init__(self):
        self.spikes = {}

    def generate_spikes(self, grid):
        self.spikes.clear()
        dirs = [(0,-1,"BOTTOM"), (0,1,"TOP"), (-1,0,"RIGHT"), (1,0,"LEFT")]

        for y in range(1, WORLD_ROWS - 1):
            for x in range(1, WORLD_COLS - 1):
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
                    if SND_EXTEND:
                        SND_EXTEND.play()
                    spike["played_sound"] = True
            elif not target_active and spike["extend_progress"] > 0.0:
                spike["extend_progress"] = max(0.0, spike["extend_progress"] - delta_time * extend_speed)
                spike["played_sound"] = False

            if spike["extend_progress"] >= 0.95 and target_x == player_x and target_y == player_y:
                hit = True
                particles.add_burst(
                    player_x * TILE_SIZE + TILE_SIZE // 2,
                    player_y * TILE_SIZE + TILE_SIZE // 2,
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

        angle_map = {"BOTTOM": 0, "TOP": 180, "RIGHT": 90, "LEFT": -90}
        angle_deg = angle_map[spike["dir"]]

        scale = 0.7 + progress * 0.5
        scaled_size = int(TILE_SIZE * scale)
        scaled = pygame.transform.scale(SPRITES[SPIKE], (scaled_size, scaled_size))
        rotated = pygame.transform.rotate(scaled, angle_deg)
        rect = rotated.get_rect(center=(current_x, current_y))
        screen.blit(rotated, rect)

# ==========================================================
# FIREBALL SYSTEM
# ==========================================================

class FireballSystem:
    def __init__(self):
        self.fireballs = []

    def generate_fireballs(self, grid):
        self.fireballs.clear()
        
        # Find horizontal corridors (rows of floor tiles)
        for y in range(1, WORLD_ROWS - 1):
            # Check if this row has a long enough corridor
            for x in range(1, WORLD_COLS - 1):
                if grid[y][x] == FLOOR and grid[y][x+1] == FLOOR:
                    # Found start of corridor, count length
                    length = 0
                    tx = x
                    while tx < WORLD_COLS and grid[y][tx] == FLOOR:
                        length += 1
                        tx += 1
                    
                    # If corridor is at least 6 tiles long, can spawn fireball
                    if length >= 6:
                        # Check if at least one end is adjacent to a wall (where fireball spawns)
                        has_wall_left = x > 0 and grid[y][x-1] == WALL
                        has_wall_right = tx < WORLD_COLS and grid[y][tx] == WALL
                        
                        if (has_wall_left or has_wall_right) and random.random() < FIREBALL_PROFUSION:
                            # Set start and end positions
                            start_x = x - 1 if has_wall_left else tx
                            end_x = x + length - 1 if has_wall_left else x - 1
                            
                            self.fireballs.append({
                                "x": start_x,
                                "y": y,
                                "start_x": start_x,
                                "end_x": end_x,
                                "direction": -1 if has_wall_left else 1,
                                "grid_y": y,  # Keep track of which row
                                "phase": random.random() * math.tau,  # Random start phase
                                "hit_last_frame": False
                            })
        
        # Find vertical corridors (columns of floor tiles)
        for x in range(1, WORLD_COLS - 1):
            for y in range(1, WORLD_ROWS - 1):
                if grid[y][x] == FLOOR and grid[y+1][x] == FLOOR:
                    length = 0
                    ty = y
                    while ty < WORLD_ROWS and grid[ty][x] == FLOOR:
                        length += 1
                        ty += 1
                    
                    if length >= 6:
                        has_wall_above = y > 0 and grid[y-1][x] == WALL
                        has_wall_below = ty < WORLD_ROWS and grid[ty][x] == WALL
                        
                        if (has_wall_above or has_wall_below) and random.random() < FIREBALL_PROFUSION:
                            # Set start and end positions
                            start_y = y - 1 if has_wall_above else ty
                            end_y = y + length - 1 if has_wall_above else y - 1
                            
                            self.fireballs.append({
                                "x": x,
                                "y": start_y,
                                "start_y": start_y,
                                "end_y": end_y,
                                "direction": -1 if has_wall_above else 1,
                                "grid_x": x,  # Keep track of which column
                                "vertical": True,
                                "phase": random.random() * math.tau,  # Random start phase
                                "hit_last_frame": False
                            })

    def update(self, delta_time, player_x, player_y, grid):
        hit = False
        
        for fb in self.fireballs:
            # Update extend progress (like spikes)
            fb["phase"] = fb.get("phase", 0) + delta_time * 2
            
            # Calculate extend progress (0 to 1 to 0 cycle)
            progress = (math.sin(fb["phase"]) + 1) / 2  # 0 to 1
            
            # Only check collision and draw when fireball is extended
            if progress > 0.3:
                # Move fireball based on extend progress
                if fb.get("vertical"):
                    # Calculate position between walls based on progress
                    start_y = fb.get("start_y", fb["y"])
                    end_y = fb.get("end_y", fb["y"])
                    fb["y"] = start_y + (end_y - start_y) * progress
                    
                    # Check collision with player (only when extended)
                    if progress > 0.5 and abs(fb["y"] - player_y) < 0.8 and fb["grid_x"] == player_x:
                        if not fb.get("hit_last_frame"):
                            hit = True
                            fb["hit_last_frame"] = True
                            particles.add_burst(
                                player_x * TILE_SIZE + TILE_SIZE // 2,
                                player_y * TILE_SIZE + TILE_SIZE // 2,
                                color=(255, 100, 0)
                            )
                else:
                    # Horizontal movement
                    start_x = fb.get("start_x", fb["x"])
                    end_x = fb.get("end_x", fb["x"])
                    fb["x"] = start_x + (end_x - start_x) * progress
                    
                    # Check collision with player (only when extended)
                    if progress > 0.5 and abs(fb["x"] - player_x) < 0.8 and fb["grid_y"] == player_y:
                        if not fb.get("hit_last_frame"):
                            hit = True
                            fb["hit_last_frame"] = True
                            particles.add_burst(
                                player_x * TILE_SIZE + TILE_SIZE // 2,
                                player_y * TILE_SIZE + TILE_SIZE // 2,
                                color=(255, 100, 0)
                            )
            
            # Reset hit flag when fireball retracts
            if progress < 0.3:
                fb["hit_last_frame"] = False
        
        return hit

    def draw(self, cam_x, cam_y):
        if not SPRITES.get("FIREBALL"):
            # Draw fallback circle if no sprite
            for fb in self.fireballs:
                px = fb["x"] * TILE_SIZE - cam_x + TILE_SIZE // 2
                py = fb["y"] * TILE_SIZE - cam_y + TILE_SIZE // 2
                pygame.draw.circle(screen, (255, 100, 0), (int(px), int(py)), TILE_SIZE // 3)
        else:
            for fb in self.fireballs:
                px = fb["x"] * TILE_SIZE - cam_x
                py = fb["y"] * TILE_SIZE - cam_y
                
                # Flip sprite based on direction
                sprite = SPRITES["FIREBALL"]
                if fb["direction"] < 0:
                    sprite = pygame.transform.flip(sprite, True, False)
                
                screen.blit(sprite, (px, py))

# ==========================================================
# PLAYER
# ==========================================================

class Player:
    def __init__(self, start, level=1, score=0, collected=None, lives=5):
        self.x, self.y = int(start[0]), int(start[1])
        self.last_safe_x, self.last_safe_y = self.x, self.y
        self.score = score
        self.lives = lives
        self.dead = False
        self.move_delay = 140
        self.last_move_time = 0
        self.level = level

        default_collected = {
            3: 0,
            4: 0,
            6: 0,
            7: 0,
            8: 0
        }
        if collected:
            default_collected.update(collected)
        self.collected = default_collected

    @property
    def health(self):
        """Health is 50% of score, capped at 100k"""
        return min(100000, int(self.score * 0.5))

    def move(self, dx, dy, grid):
        now = pygame.time.get_ticks()
        if now - self.last_move_time < self.move_delay:
            return
        if dx == 0 and dy == 0:
            return

        self.last_move_time = now
        nx = max(0, min(WORLD_COLS - 1, self.x + dx))
        ny = max(0, min(WORLD_ROWS - 1, self.y + dy))

        tile = grid[ny][nx]
        if tile == WALL:
            return

        if tile == TRAP:
            self.x, self.y = nx, ny
            particles.add_burst(
                nx * TILE_SIZE + TILE_SIZE // 2,
                ny * TILE_SIZE + TILE_SIZE // 2,
                color=(100, 50, 0)
            )
            if SND_TRAP_FALL:
                SND_TRAP_FALL.play()
            self.dead = True
            return "TRAP_DEATH"

        if tile in ITEM_TYPES:
            old_score = self.score
            self.score += ITEM_TYPES[tile]["points"]
            
            # Check if score went negative (from poison) - lose a life
            if self.score < 0:
                self.score = 0
                self.lives -= 1
                persistent_lives = self.lives
                self.collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                particles.add_burst(
                    self.x * TILE_SIZE + TILE_SIZE // 2,
                    self.y * TILE_SIZE + TILE_SIZE // 2,
                    color=(255, 0, 0)
                )
                if self.lives <= 0:
                    self.dead = True
                    return "NEGATIVE_DEATH"
            else:
                # Check for extra life every 250k points
                old_lives_threshold = old_score // EXTRA_LIFE_THRESHOLD
                new_lives_threshold = self.score // EXTRA_LIFE_THRESHOLD
                if new_lives_threshold > old_lives_threshold:
                    self.lives += 1
                    persistent_lives = self.lives
                    # Play extra life sound
                    if SND_EXTRA_LIFE:
                        SND_EXTRA_LIFE.play()
                    # Show extra life message
                    particles.add_burst(
                        self.x * TILE_SIZE + TILE_SIZE // 2,
                        self.y * TILE_SIZE + TILE_SIZE // 2,
                        color=(0, 255, 255)
                    )
            
            self.collected[tile] += 1
            if SND_PICKUP:
                SND_PICKUP.play()
            grid[ny][nx] = FLOOR

        if tile == GOAL:
            return "NEXT"

        self.x, self.y = nx, ny
        self.last_safe_x, self.last_safe_y = nx, ny

# ==========================================================
# UTILITIES
# ==========================================================

camera_x = 0
camera_y = 0

def get_camera(player):
    global camera_x, camera_y
    target_x = player.x * TILE_SIZE - SCREEN_WIDTH // 2
    target_y = player.y * TILE_SIZE - SCREEN_HEIGHT // 2
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
    scores = sorted(scores, reverse=True)[:5]
    with open("highscores.txt", "w") as f:
        for s in scores:
            f.write(str(s) + "\n")

def draw_torch(player):
    w, h = screen.get_size()
    darkness = pygame.Surface((w, h), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 220))
    pygame.draw.circle(darkness, (0, 0, 0, 0), (w // 2, h // 2), 200)
    screen.blit(darkness, (0, 0))

def draw_minimap(grid, player):
    mini = pygame.Surface((200, 200))
    mini.fill((20, 20, 20))
    scale = 200 / WORLD_COLS
    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] == FLOOR:
                pygame.draw.rect(mini, (90, 90, 90), (x * scale, y * scale, 2, 2))
    pygame.draw.rect(mini, (255, 0, 0), (player.x * scale, player.y * scale, 4, 4))
    screen.blit(mini, (SCREEN_WIDTH - 210, 10))

def draw_world_scene():
    cam_x, cam_y = get_camera(player)
    screen.fill((0, 0, 0))

    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            rect = pygame.Rect(x * TILE_SIZE - cam_x, y * TILE_SIZE - cam_y, TILE_SIZE, TILE_SIZE)
            if not rect.colliderect(screen.get_rect()):
                continue

            tile = grid[y][x]

            if tile == FLOOR or tile in ITEM_TYPES or tile == GOAL or tile == TRAP:
                if SPRITES.get(FLOOR):
                    screen.blit(SPRITES[FLOOR], rect)
                else:
                    pygame.draw.rect(screen, (90, 90, 110), rect)

            if tile == TRAP:
                if SPRITES.get(TRAP):
                    screen.blit(SPRITES[TRAP], rect)
                else:
                    pygame.draw.rect(screen, (50, 50, 60), rect)

            if tile in ITEM_TYPES and ITEM_TYPES[tile].get("image"):
                img = ITEM_TYPES[tile]["image"]
                screen.blit(img, rect)
            elif tile == GOAL and SPRITES.get(GOAL):
                screen.blit(SPRITES[GOAL], rect)

    for spike in spike_system.spikes.values():
        spike_system.draw_spike(spike, cam_x, cam_y)
    
    # Draw fireballs
    fireball_system.draw(cam_x, cam_y)

    px = player.x * TILE_SIZE - cam_x
    py = player.y * TILE_SIZE - cam_y
    if PLAYER_SPRITE:
        screen.blit(PLAYER_SPRITE, (px, py))
    else:
        pygame.draw.rect(screen, (0, 120, 255), (px, py, TILE_SIZE, TILE_SIZE))

    particles.draw(cam_x, cam_y)
    draw_torch(player)
    draw_minimap(grid, player)
    draw_stats_bar()

def draw_fall_transition():
    global current_message_bg_img
    
    elapsed = pygame.time.get_ticks() - fall_start_time
    progress = min(1.0, elapsed / fall_duration)

    # Use fall background if available
    if FALL_BACKGROUNDS:
        if current_message_bg_img is None:
            current_message_bg_img = FALL_BACKGROUNDS[0] if len(FALL_BACKGROUNDS) == 1 else random.choice(FALL_BACKGROUNDS)
        screen.blit(current_message_bg_img, (0, 0))
    else:
        screen.fill((0, 0, 0))

    cx = SCREEN_WIDTH // 2
    cy = SCREEN_HEIGHT // 2
    max_radius = int(math.hypot(SCREEN_WIDTH, SCREEN_HEIGHT))

    num_arcs = 40
    for i in range(num_arcs):
        spiral_progress = progress + i * 0.025
        radius = max_radius * (1.0 - spiral_progress)
        if radius <= 0:
            continue

        angle = spiral_progress * math.tau * 3 + i * 0.4
        x = cx + math.cos(angle) * radius * 0.3
        y = cy + math.sin(angle) * radius * 0.3

        alpha = max(0, min(255, int(220 * progress)))
        size = max(10, int(radius * 0.08))

        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (0, 0, 0, alpha), (size, size), size)
        screen.blit(surf, (x - size, y - size))

    hole_radius = int((progress ** 1.8) * max_radius)
    hole = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(hole, (0, 0, 0, 230), (cx, cy), hole_radius)
    screen.blit(hole, (0, 0))

    if progress < 0.7:
        text_alpha = int(255 * (1.0 - progress / 0.7))
        msg = big_font.render("YOU FELL!", True, (255, 80, 80))
        msg.set_alpha(text_alpha)
        screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 120))

# ==========================================================
# LEVEL SUMMARY SCREEN
# ==========================================================

def draw_level_summary(level, score_gained, total_score):
    screen.fill((5, 5, 20))

    title = huge_font.render("LEVEL COMPLETE!", True, COLOR_GOLD)
    title_glow = huge_font.render("LEVEL COMPLETE!", True, COLOR_SUN_GLOW)
    screen.blit(title_glow, (SCREEN_WIDTH // 2 - title_glow.get_width() // 2 + 2, 140))
    screen.blit(title_glow, (SCREEN_WIDTH // 2 - title_glow.get_width() // 2 - 2, 140))
    screen.blit(title_glow, (SCREEN_WIDTH // 2 - title_glow.get_width() // 2, 142))
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 140))

    lvl_text = font.render(f"🏆  Level {level - 1} Conquered!  🏆", True, COLOR_GREEN)
    gain_text = font.render(f"💰  Score Gained: +{score_gained:,}  💰", True, COLOR_GOLD)
    total_text = font.render(f"⭐  Total Score: {total_score:,}  ⭐", True, COLOR_PURPLE)

    screen.blit(lvl_text, (SCREEN_WIDTH // 2 - lvl_text.get_width() // 2, 280))
    screen.blit(gain_text, (SCREEN_WIDTH // 2 - gain_text.get_width() // 2, 330))
    screen.blit(total_text, (SCREEN_WIDTH // 2 - total_text.get_width() // 2, 380))

    sun_center = (SCREEN_WIDTH // 2, 500)

    for ring in range(4):
        glow_size = 70 + ring * 15 + math.sin(pygame.time.get_ticks() * 0.01 + ring) * 10
        glow_alpha = 100 - ring * 20
        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*COLOR_SUN_GLOW, glow_alpha), (glow_size, glow_size), glow_size)
        screen.blit(glow_surf, (sun_center[0] - glow_size, sun_center[1] - glow_size))

    pygame.draw.circle(screen, COLOR_SUN, sun_center, 65)
    pygame.draw.circle(screen, (255, 255, 150), sun_center, 55)
    pygame.draw.circle(screen, COLOR_SUN, sun_center, 45)

    for i in range(16):
        angle = i * math.tau / 16
        end_x = sun_center[0] + math.cos(angle) * 85
        end_y = sun_center[1] + math.sin(angle) * 85
        pygame.draw.line(screen, COLOR_SUN_GLOW, sun_center, (end_x, end_y), 8)

    prompt = font.render("🎮  Press ANY KEY for Next Challenge  🎮", True, COLOR_BLUE)
    screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 670))

# ==========================================================
# NARRATIVE SCREEN
# ==========================================================

def load_narratives():
    try:
        with open("narratives.json", "r") as f:
            data = json.load(f)
            return data.get("narratives", [])
    except (FileNotFoundError, json.JSONDecodeError):
        print("Warning: narratives.json not found or invalid")
        return []

def get_narrative_for_level(level, narratives):
    for n in narratives:
        if n.get("level") == level:
            return n

    if narratives:
        return narratives[(level - 1) % len(narratives)]

    return {"title": f"Level {level}", "story": "A new challenge awaits..."}

# ==========================================================
# NARRATIVE BACKGROUNDS
# ==========================================================

NARRATIVE_BG_FILES = [
    "narrative_01.jpg",
    "narrative_02.png",
    "narrative_03.png",
]

# Message screen backgrounds
LIFE_LOSS_BG_FILES = [
    "lostlife.png",
]

FALL_BG_FILES = [
    "pit.jpg",
]

def load_narrative_backgrounds():
    backgrounds = []
    for name in NARRATIVE_BG_FILES:
        path = os.path.join(ASSET_PATH, name)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                img = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                backgrounds.append(img)
            except pygame.error as e:
                print(f"Warning: could not load narrative background {name}: {e}")
        else:
            print(f"Warning: narrative background not found: {path}")
    return backgrounds

def choose_narrative_background():
    global current_narrative_bg
    if NARRATIVE_BACKGROUNDS:
        current_narrative_bg = random.choice(NARRATIVE_BACKGROUNDS)
    else:
        current_narrative_bg = None

NARRATIVE_BACKGROUNDS = load_narrative_backgrounds()
current_narrative_bg = None

# Load life loss backgrounds
def load_message_backgrounds(file_list):
    backgrounds = []
    for name in file_list:
        path = os.path.join(ASSET_PATH, name)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                img = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
                backgrounds.append(img)
            except pygame.error as e:
                print(f"Warning: could not load {name}: {e}")
    return backgrounds

LIFE_LOSS_BACKGROUNDS = load_message_backgrounds(LIFE_LOSS_BG_FILES)
FALL_BACKGROUNDS = load_message_backgrounds(FALL_BG_FILES)

current_message_bg = None  # For message screens

def draw_narrative(level, title, story):
    screen.fill((0, 0, 0))

    # Draw background image if available, otherwise use gradient fallback
    if current_narrative_bg:
        screen.blit(current_narrative_bg, (0, 0))

        # Fade the image so text reads clearly on top
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fade.fill((0, 0, 0, 110))
        screen.blit(fade, (0, 0))
    else:
        for i in range(SCREEN_HEIGHT):
            t = i / SCREEN_HEIGHT
            r = int(30 + 40 * t)
            g = int(10 + 20 * t)
            b = int(50 + 30 * t)
            pygame.draw.line(screen, (r, g, b), (0, i), (SCREEN_WIDTH, i))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

    # Optional extra text panel for readability
    text_panel = pygame.Surface((SCREEN_WIDTH - 120, 360), pygame.SRCALPHA)
    text_panel.fill((0, 0, 0, 110))
    panel_x = 60
    panel_y = 150
    screen.blit(text_panel, (panel_x, panel_y))

    title_text = big_font.render(title, True, COLOR_GOLD)
    title_shadow = big_font.render(title, True, (100, 50, 0))
    screen.blit(title_shadow, (SCREEN_WIDTH // 2 - title_text.get_width() // 2 + 3, 183))
    screen.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 180))

    words = story.split()
    lines = []
    current_line = []
    max_width = SCREEN_WIDTH - 160

    for word in words:
        test_line = " ".join(current_line + [word])
        test_surface = font.render(test_line, True, (255, 255, 255))
        if test_surface.get_width() <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    y_start = 300
    line_height = 35
    for i, line in enumerate(lines):
        text_shadow = font.render(line, True, (20, 20, 20))
        text = font.render(line, True, (235, 235, 240))
        x = SCREEN_WIDTH // 2 - text.get_width() // 2
        y = y_start + i * line_height
        screen.blit(text_shadow, (x + 2, y + 2))
        screen.blit(text, (x, y))

    level_text = font.render(f"~ Level {level} ~", True, COLOR_PURPLE)
    screen.blit(level_text, (SCREEN_WIDTH // 2 - level_text.get_width() // 2, 560))

    prompt = font.render("Press ANY KEY to Continue", True, COLOR_BLUE)
    screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 640))

# ==========================================================
# MESSAGE SCREEN (Life loss, etc.)
# ==========================================================

# Track current message background
current_message_bg_img = None
message_bg_initialized = False

def draw_message_screen(message, color=COLOR_RED, msg_type="life_loss"):
    """Draw a message screen with appropriate background"""
    global current_message_bg_img, message_bg_initialized
    
    # Select background based on message type
    if msg_type == "fall":
        bg_list = FALL_BACKGROUNDS
    if msg_type == "life_loss":
        bg_list = LIFE_LOSS_BACKGROUNDS
    
    # Pick one background when message starts and keep it
    if bg_list and not message_bg_initialized:
        current_message_bg_img = random.choice(bg_list) if len(bg_list) > 1 else bg_list[0]
        message_bg_initialized = True
    
    if bg_list and current_message_bg_img:
        
        screen.blit(current_message_bg_img, (0, 0))
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fade.fill((0, 0, 0, 150))
        screen.blit(fade, (0, 0))
    else:
        screen.fill((0, 0, 0))
    
    # Draw the message
    msg_surf = big_font.render(message, True, color)
    screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
    
    # Draw lives remaining (only for life loss messages)
    if msg_type == "life_loss" and player:
        lives_msg = font.render(f"Lives remaining: {player.lives}", True, COLOR_RED)
        screen.blit(lives_msg, (SCREEN_WIDTH // 2 - lives_msg.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

# ==========================================================
# GAME STATES
# ==========================================================

STATE_SPLASH = 0
STATE_PLAY = 1
STATE_SUMMARY = 2
STATE_GAMEOVER = 3
STATE_NARRATIVE = 4
STATE_FALLING = 5
STATE_MESSAGE = 6  # For life loss messages

state = STATE_SPLASH
grid = None
player = None
spike_system = SpikeSystem()
fireball_system = FireballSystem()
particles = ParticleSystem()
last_time = pygame.time.get_ticks()
last_level_score = 0

fall_start_time = 0
fall_duration = 1200
death_type = None

narratives = load_narratives()
current_narrative = None

# Message screen variables
message_text = ""
message_type = "life_loss"  # "life_loss" or "fall"
message_start_time = 0
message_duration = 1500

persistent_level = 1
persistent_score = 0
persistent_lives = 5
persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0}

# ==========================================================
# SPLASH SCREEN
# ==========================================================

def draw_splash():
    screen.fill((0, 0, 0))

    ascii_title = [
        "  ██████╗ ██████╗ ██╗   ██╗ ██████╗███████╗",
        "  ██╔══██╗██╔══██╗██║   ██║██╔════╝██╔════╝",
        "  ██████╔╝██████╔╝██║   ██║██║     █████╗  ",
        "  ██╔══██╗██╔══██╗██║   ██║██║     ██╔══╝  ",
        "  ██████╔╝██║  ██║╚██████╔╝╚██████╗███████╗",
        "  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝",
        "",
        "v1.0",
        "",
        "BRUCE'S TREASURE",
        "",
        "> PRESS ANY KEY TO BEGIN <",
    ]

    line_spacing = 35
    total_height = len(ascii_title) * line_spacing
    start_y = (SCREEN_HEIGHT // 2) - (total_height // 2)

    for i, line in enumerate(ascii_title):
        text = font.render(line, True, (0, 255, 0))
        current_y = start_y + (i * line_spacing)
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, current_y))
        screen.blit(text, rect)

def find_safe_spawn(grid, candidate_x, candidate_y):
    if grid[int(candidate_y)][int(candidate_x)] == FLOOR:
        return int(candidate_x), int(candidate_y)

    for radius in range(1, 12):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) != radius:
                    continue
                nx = int(candidate_x) + dx
                ny = int(candidate_y) + dy
                if (0 <= nx < WORLD_COLS and
                    0 <= ny < WORLD_ROWS and
                    grid[ny][nx] == FLOOR):
                    return nx, ny

    print("WARNING: No safe spawn found near", candidate_x, candidate_y)
    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] == FLOOR:
                return x, y
    return 5, 5

def start_level(level_number):
    global grid, player, last_level_score, current_narrative
    global persistent_score, persistent_collected, persistent_lives

    grid, suggested_start = generate_world()
    safe_x, safe_y = find_safe_spawn(grid, suggested_start[0], suggested_start[1])

    player = Player(
        (safe_x, safe_y),
        level=level_number,
        score=persistent_score,
        collected=persistent_collected.copy(),
        lives=persistent_lives
    )

    place_items(grid)

    goal_pos = None
    for y in range(WORLD_ROWS):
        for x in range(WORLD_COLS):
            if grid[y][x] == GOAL:
                goal_pos = (x, y)
                break
        if goal_pos:
            break

    place_traps(grid, (safe_x, safe_y), goal_pos or (WORLD_COLS // 2, WORLD_ROWS // 2))
    spike_system.generate_spikes(grid)
    fireball_system.generate_fireballs(grid)
    particles.particles.clear()
    last_level_score = player.score

# ==========================================================
# MAIN LOOP
# ==========================================================

while True:
    clock.tick(FPS)
    current_time = pygame.time.get_ticks()
    delta_time = (current_time - last_time) / 1000.0
    last_time = current_time

    for event in pygame.event.get():
        if event.type == SONG_FINISHED:
            play_next_song()

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if state == STATE_SPLASH:
                persistent_level = 1
                persistent_score = 0
                persistent_lives = 5
                persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                current_narrative = get_narrative_for_level(persistent_level, narratives)
                choose_narrative_background()
                state = STATE_NARRATIVE

            elif state == STATE_SUMMARY:
                persistent_level += 1
                current_narrative = get_narrative_for_level(persistent_level, narratives)
                choose_narrative_background()
                state = STATE_NARRATIVE

            elif state == STATE_NARRATIVE:
                start_level(persistent_level)
                state = STATE_PLAY

            elif state == STATE_GAMEOVER:
                persistent_level = 1
                persistent_score = 0
                persistent_lives = 5
                persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                state = STATE_SPLASH

    if state == STATE_SPLASH:
        draw_splash()
        pygame.display.flip()
        continue

    elif state == STATE_PLAY:
        particles.update(delta_time)
        player.dead = spike_system.update(delta_time, player.x, player.y, particles)
        
        # Update fireballs and check for hits
        fireball_hit = fireball_system.update(delta_time, player.x, player.y, grid)
        if fireball_hit and not player.dead:
            # Fireball hit deals damage
            player.score = max(0, player.score - FIREBALL_DAMAGE)
            # Check if health dropped to 0 or below (lose a life)
            if player.health <= 0:
                player.lives -= 1
                persistent_lives = player.lives
                player.score = 0
                player.collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                persistent_score = 0
                persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                particles.add_burst(
                    player.x * TILE_SIZE + TILE_SIZE // 2,
                    player.y * TILE_SIZE + TILE_SIZE // 2,
                    color=(255, 0, 0)
                )
                if player.lives <= 0:
                    save_score(persistent_score)
                    state = STATE_GAMEOVER
                else:
                    message_text = "You lost a life!"
                    message_type = "life_loss"
                    message_start_time = pygame.time.get_ticks()
                    state = STATE_MESSAGE

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1

        result = player.move(dx, dy, grid)

        if result == "TRAP_DEATH":
            death_type = "trap"
            if SND_FALL:
                SND_FALL.play()
            # 50% chance to climb out
            if random.random() < 0.5:
                # Player climbed out - show message and stay in game
                player.x = player.last_safe_x
                player.y = player.last_safe_y
                # Show "you climbed out" message using message screen
                message_text = "You climbed out!"
                message_type = "fall"
                message_start_time = pygame.time.get_ticks()
                message_bg_initialized = False  # Reset background for new message
                state = STATE_MESSAGE
            else:
                # Player couldn't climb out - lose a life
                player.lives -= 1
                persistent_lives = player.lives
                
                # Lost a life - reset score and items, keep level progression
                player.score = 0
                player.collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                persistent_score = 0
                persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                
                # Show "You lost a life!" message
                message_text = "You lost a life!"
                message_type = "life_loss"
                message_start_time = pygame.time.get_ticks()
                message_bg_initialized = False  # Reset background for new message
                
                # Check if out of lives
                if player.lives <= 0:
                    fall_start_time = pygame.time.get_ticks()
                    state = STATE_FALLING
                else:
                    state = STATE_MESSAGE
            continue

        if player.dead:
            if SND_SPIKE_HIT:
                SND_SPIKE_HIT.play()
            elif SND_SPIKE:
                SND_SPIKE.play()
            # Spike hit deals damage instead of instant death
            player.score = max(0, player.score - SPIKE_DAMAGE)
            player.dead = False  # Reset dead flag
            # Check if health dropped to 0 or below (lose a life)
            if player.health <= 0:
                player.lives -= 1
                persistent_lives = player.lives
                # Lost a life - reset score and items, keep level progression
                player.score = 0
                player.collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                persistent_score = 0
                persistent_collected = {3: 0, 4: 0, 6: 0, 7: 0, 8: 0, 90: 0, 100: 0, 110: 0, 120: 0, 130: 0}
                particles.add_burst(
                    player.x * TILE_SIZE + TILE_SIZE // 2,
                    player.y * TILE_SIZE + TILE_SIZE // 2,
                    color=(255, 0, 0)
                )
                # Check if out of lives
                if player.lives <= 0:
                    save_score(persistent_score)
                    state = STATE_GAMEOVER
                else:
                    # Show message screen
                    message_text = "You lost a life!"
                    message_type = "life_loss"
                    message_start_time = pygame.time.get_ticks()
                    message_bg_initialized = False  # Reset background for new message
                    state = STATE_MESSAGE
            continue

        if result == "NEXT":
            persistent_score = player.score
            persistent_collected = player.collected.copy()
            if SND_WIN:
                SND_WIN.play()
            state = STATE_SUMMARY
            continue

        if result == "NEGATIVE_DEATH":
            # Score went negative (poison) - show message, game over if out of lives
            if player.lives <= 0:
                save_score(player.score)
                state = STATE_GAMEOVER
            else:
                message_text = "You lost a life!"
                message_type = "life_loss"
                message_start_time = pygame.time.get_ticks()
                message_bg_initialized = False  # Reset background for new message
                state = STATE_MESSAGE
            continue

        draw_world_scene()
        pygame.display.flip()

    elif state == STATE_SUMMARY:
        draw_level_summary(player.level, player.score - last_level_score, player.score)
        pygame.display.flip()
        continue

    elif state == STATE_NARRATIVE:
        display_level = current_narrative.get("level", persistent_level) if current_narrative else persistent_level
        draw_narrative(display_level, current_narrative.get("title", ""), current_narrative.get("story", ""))
        pygame.display.flip()
        continue

    elif state == STATE_MESSAGE:
        # Determine message color based on content
        if "climbed out" in message_text.lower():
            msg_color = COLOR_GREEN
        else:
            msg_color = COLOR_RED
        
        draw_message_screen(message_text, msg_color, message_type)
        pygame.display.flip()
        
        # Check if message duration has passed
        if pygame.time.get_ticks() - message_start_time >= message_duration:
            # Return to play state
            state = STATE_PLAY
        continue

    elif state == STATE_FALLING:
        draw_fall_transition()
        pygame.display.flip()

        if pygame.time.get_ticks() - fall_start_time >= fall_duration:
            save_score(player.score)
            state = STATE_GAMEOVER
        continue

    elif state == STATE_GAMEOVER:
        screen.fill((0, 0, 0))
        over = big_font.render("GAME OVER", True, COLOR_RED)
        screen.blit(over, (SCREEN_WIDTH // 2 - over.get_width() // 2, 200))
        
        lives_msg = font.render("Out of lives!", True, COLOR_RED)
        screen.blit(lives_msg, (SCREEN_WIDTH // 2 - lives_msg.get_width() // 2, 280))

        scores = load_scores()
        y = 350
        title_hs = font.render("HIGH SCORES", True, COLOR_GOLD)
        screen.blit(title_hs, (SCREEN_WIDTH // 2 - title_hs.get_width() // 2, y))
        y += 50

        for i, s in enumerate(scores):
            hs_text = font.render(f"{i + 1}. {s:,}", True, COLOR_SUN_GLOW)
            screen.blit(hs_text, (SCREEN_WIDTH // 2 - hs_text.get_width() // 2, y))
            y += 35

        restart = font.render("Press ESC to Quit | Any Key to Restart", True, COLOR_BLUE)
        screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 620))

        pygame.display.flip()

# Clean exit
pygame.quit()
sys.exit()