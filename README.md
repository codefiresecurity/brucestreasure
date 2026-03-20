# Bruce's Treasure - Technical Documentation

## Table of Contents

1. [Game Overview](#game-overview)
2. [Architecture](#architecture)
3. [Configuration Constants](#configuration-constants)
4. [Core Systems](#core-systems)
5. [Game States](#game-states)
6. [Entity Relationships](#entity-relationships)
7. [Main Game Loop](#main-game-loop)

---

## Game Overview

Bruce's Treasure is a pygame-based dungeon crawler game where the player navigates procedurally generated dungeons, collects items, avoids hazards (spikes and traps), and progresses through levels to reach the Sun Treasure.

### Core Gameplay Loop

```mermaid
flowchart TD
    A[Start Game] --> B[Splash Screen]
    B --> C{Narrative Screen}
    C --> D[Generate World]
    D --> E[Place Items & Hazards]
    E --> F[Play Level]
    F --> G{Hazards Triggered?}
    G -->|Yes| H[Death Animation]
    G -->|No| I{Goal Reached?}
    I -->|No| F
    I -->|Yes| J[Level Summary]
    J --> C
    H --> K[Game Over]
    K --> L[High Scores]
    L --> B
```

---

## Architecture

### System Overview

```mermaid
flowchart TB
    subgraph Core["Core Systems"]
        Init["Initialization<br/>pygame.init()"]
        Config["Configuration<br/>Constants"]
        Assets["Asset Loading<br/>Sprites & Audio"]
    end

    subgraph Generation["World Generation"]
        WorldGen["generate_world()"]
        ItemPlace["place_items()"]
        TrapPlace["place_traps()"]
        SpikeGen["spike_system.generate_spikes()"]
    end

    subgraph Entities["Game Entities"]
        Player["Player Class"]
        Spikes["SpikeSystem Class"]
        Particles["ParticleSystem Class"]
    end

    subgraph UI["User Interface"]
        StatsBar["draw_stats_bar()"]
        Minimap["draw_minimap()"]
        Torch["draw_torch()"]
    end

    subgraph States["Game States"]
        Splash["Splash Screen"]
        Narrative["Narrative Screen"]
        Play["Play State"]
        Summary["Level Summary"]
        GameOver["Game Over"]
        Falling["Death Animation"]
    end

    Init --> Config
    Config --> Assets
    Assets --> Generation
    Generation --> Entities
    Entities --> States
    States --> UI
```

### File Structure

```
brucestreasure/
├── main.py              # Main game file (1074 lines)
├── narratives.json      # Level story text
├── highscores.txt       # Persistent high scores
├── assets/              # Game assets
│   ├── *.png           # Sprite images
│   ├── *.ogg           # Music tracks
│   ├── *.wav           # Sound effects
│   └── music.mp3       # Background music
└── README.md           # This documentation
```

---

## Configuration Constants

The game uses several configuration constants defined at the top of [`main.py`](main.py:1):

### World Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `TILE_SIZE` | 32 | Size of each tile in pixels |
| `WORLD_COLS` | 120 | Number of columns in the world grid |
| `WORLD_ROWS` | 120 | Number of rows in the world grid |
| `VISIBLE_COLS` | Dynamic | Columns visible on screen |
| `VISIBLE_ROWS` | Dynamic | Rows visible on screen |

### Tile Types

| Constant | Value | Description |
|----------|-------|-------------|
| `FLOOR` | 0 | Walkable floor tile |
| `WALL` | 1 | Solid wall - blocks movement |
| `SPIKE` | 2 | Hazard that extends/retracts |
| `TRAP` | 10 | Hole that kills player on step |
| `GOAL` | 9 | Sun treasure - level completion |

### Difficulty Parameters

| Constant | Value | Description |
|----------|-------|-------------|
| `SPIKE_PROFUSION` | 0.07 | Probability of spike generation (7%) |
| `TRAP_PROFUSION` | 0.08 | Probability of trap placement (8%) |
| `MIN_PATH_WIDTH` | 2 | Minimum corridor width |
| `FIREBALL_PROFUSION` | 0.03 | Probability of fireball generation (3%) |
| `SPIKE_DAMAGE` | 20 | Damage taken when hit by a spike |
| `FIREBALL_DAMAGE` | 25 | Damage taken when hit by a fireball |
| `EXTRA_LIFE_THRESHOLD` | 250000 | Points needed to earn an extra life |
| `HEALTH_CAP` | 100000 | Maximum health value (50% of score, capped) |

---

## Core Systems

### 1. Asset Loading System

The game loads sprites and audio files from the `assets/` directory.

```mermaid
flowchart LR
    subgraph Loading["Asset Loading"]
        load_sprite["load_sprite()<br/>Lines 99-104"]
        load_sound["load_sound()<br/>Lines 65-69"]
        play_next_song["play_next_song()<br/>Lines 75-85"]
    end

    subgraph Sprites["Loaded Sprites"]
        FLOOR["floor.png"]
        WALL["wall.png"]
        SPIKE["spike.png"]
        TRAP["floor.png (darkened)"]
        GOAL["sun.png"]
        PLAYER["player.png"]
    end

    subgraph Items["Item Sprites"]
        COIN["coin.png"]
        MUSHROOM["mushroom.png"]
        TROPHY["trophy.png"]
        POISON["poison.png"]
        GEMS["gem*.png"]
    end

    load_sprite --> Sprites
    load_sprite --> Items
    load_sound --> AUDIO
    play_next_song --> AUDIO
```

#### Sound Loading ([`main.py:65-94`](main.py:65))

```python
def load_sound(name):
    """Load a sound file from assets directory."""
    path = os.path.join(ASSET_PATH, name)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None
```

The game loads the following sounds:
- `hit.wav` - Spike damage sound
- `coin.wav` - Item pickup sound
- `spike_extend.wav` - Spike activation sound
- `win.wav` - Level completion sound
- `trap_fall.wav` - Trap fall sound

#### Music Playlist ([`main.py:71`](main.py:71))

```python
MUSIC_PLAYLIST = ["music.mp3", "01.ogg", "02.ogg", "03.ogg", "04.ogg", 
                  "05.ogg", "06.ogg", "07.ogg", "08.ogg"]
```

Songs are randomly selected and played in a loop using pygame's `USEREVENT` system.

---

### 2. World Generation System

The dungeon is procedurally generated using a room-and-corridor algorithm.

```mermaid
flowchart TD
    A[generate_world] --> B[Initialize Grid with WALLS]
    B --> C{Generate Rooms Loop<br/>12 rooms}
    C -->|Try| D[Random Room Size<br/>8-15 x 8-15]
    D --> E[Check Overlap]
    E -->|Overlap| C
    E -->|No Overlap| F[Carve Room FLOOR]
    F --> C
    C -->|Done| G{Connect Rooms<br/>Corridors}
    G --> H[Horizontal or Vertical<br/>Corridor Choice]
    H --> I[Carve 2-tile Wide Path]
    I --> J[Place GOAL Tile]
    J --> K[Return grid, start_pos]
```

#### Room Generation ([`main.py:233-294`](main.py:233))

```python
def generate_world():
    """Generate a procedural dungeon with rooms and corridors."""
    grid = [[WALL for _ in range(WORLD_COLS)] for _ in range(WORLD_ROWS)]
    rooms = []

    # Generate 12 non-overlapping rooms
    for _ in range(12):
        w = random.randint(8, 15)
        h = random.randint(8, 15)
        x = random.randint(3, WORLD_COLS - w - 3)
        y = random.randint(3, WORLD_ROWS - h - 3)

        new_room = pygame.Rect(x, y, w, h)
        # Check collision with existing rooms (with padding)
        # ...
```

#### Corridor Generation ([`main.py:256-279`](main.py:256))

Rooms are connected using 2-tile wide corridors:
- If horizontal distance > vertical distance: horizontal corridor
- Otherwise: vertical corridor

```python
# Corridor carving logic
if abs(door1_x - door2_x) > abs(door1_y - door2_y):
    # Horizontal corridor with 2-tile width
    for x in range(min(door1_x, door2_x) - 1, max(door1_x, door2_x) + 2):
        for lane in [0, 1]:
            grid[int(door1_y + lane)][int(x)] = FLOOR
```

---

### 3. Item Placement System

Items are randomly placed on floor tiles based on spawn probabilities.

```mermaid
flowchart TD
    A[place_items] --> B[Iterate All Grid Cells]
    B --> C{Is FLOOR Tile?}
    C -->|No| B
    C -->|Yes| D{Too Close to<br/>SPIKE or GOAL?}
    D -->|Yes| B
    D -->|No| E[Random Roll]
    E --> F{Which Item?}
    F --> G[Coin: 10pts<br/>spawn: 0.02]
    F --> H[Mushroom: 25pts<br/>spawn: 0.01]
    F --> I[Trophy: 100pts<br/>spawn: 0.005]
    F --> J[Poison: -100pts<br/>spawn: 0.01]
    F --> K[Coins: 200pts<br/>spawn: 0.002]
    F --> L[Gems: 10k-100kpts<br/>spawn: 0.002 each]
    G --> M[Place Item on Grid]
    H --> M
    I --> M
    J --> M
    K --> M
    L --> M
```

#### Item Types ([`main.py:160-171`](main.py:160))

```python
ITEM_TYPES = {
    3: {"name": "Coin", "points": 10, "spawn": 0.02, "sprite": "coin.png"},
    4: {"name": "Mushroom", "points": 25, "spawn": 0.01, "sprite": "mushroom.png"},
    6: {"name": "Trophy", "points": 100, "spawn": 0.005, "sprite": "trophy.png"},
    7: {"name": "Poison", "points": -100, "spawn": 0.01, "sprite": "poison.png"},
    8: {"name": "Coins", "points": 200, "spawn": 0.002, "sprite": "coins.png"},
    90: {"name": "Medium Yellow Gem", "points": 10000, "spawn": 0.002},
    100: {"name": "Big Yellow Gem", "points": 100000, "spawn": 0.002},
    110: {"name": "Purple Gem", "points": 80000, "spawn": 0.002},
    120: {"name": "Blue Gem", "points": 80000, "spawn": 0.002},
    130: {"name": "Green Gem", "points": 80000, "spawn": 0.002}
}
```

---

### 4. Hazard Systems

#### Spike System

Spikes are timed hazards that extend from walls into adjacent floor tiles.

```mermaid
flowchart TD
    A[SpikeSystem.generate_spikes] --> B[Iterate All Floor Tiles]
    B --> C{Adjacent to WALL?}
    C -->|No| B
    C -->|Yes| D{Random < SPIKE_PROFUSION?}
    D -->|No| B
    D -->|Yes| E[Create Spike<br/>4 directions possible]
    E --> F[Store in spikes dict<br/>key: x,y,direction]
    F --> B
    
    G[SpikeSystem.update] --> H[For Each Spike]
    H --> I["Update Phase<br/>sin(phase) determines active"]
    I --> J{Extend or Retract?}
    J -->|Extend| K[progress += delta * 5]
    J -->|Retract| L[progress -= delta * 2.5]
    K --> M{progress > 0.3<br/>and not played_sound?}
    L --> M
    M -->|Yes| N[Play SND_EXTEND]
    M --> No
    N --> O[played_sound = True]
    O --> P{progress >= 0.95<br/>and at player pos?}
    P -->|Yes| Q[Return hit = True]
    P -->|No| H
```

#### Spike Properties ([`main.py:374-450`](main.py:374))

```python
class SpikeSystem:
    def __init__(self):
        self.spikes = {}  # Dictionary of active spikes

    def generate_spikes(self, grid):
        # Spikes spawn on floor tiles next to walls
        # Direction: BOTTOM, TOP, RIGHT, LEFT
        # Each spike has: origin, target, direction, phase, extend_progress
```

Spike animation:
- Uses sine wave for extend/retract cycle
- Extends faster (speed 5) than retracts (speed 2.5)
- Becomes dangerous at 95% extension
- Sound plays at 30% extension

#### Trap System

Traps are holes that instantly kill the player when stepped on.

```mermaid
flowchart TD
    A[place_traps] --> B[Safe Radius Check]
    B --> C{Distance from Start<br/>> 8 tiles?}
    C -->|No| Skip[Skip This Tile]
    C -->|Yes| D{Distance from Goal<br/>> 8 tiles?}
    D -->|No| Skip
    D -->|Yes| E{Too Close to SPIKE?}
    E -->|Yes| Skip
    E -->|No| F{Create Dead End?}
    F -->|Yes| Skip
    F -->|No| G{Random < TRAP_PROFUSION?}
    G -->|Yes| H[Place TRAP]
    G -->|No| Skip
```

#### Trap Placement Rules ([`main.py:326-359`](main.py:326))

```python
def place_traps(grid, start_pos, goal_pos):
    safe_radius = 8  # Minimum distance from start/goal
    
    # Skip if:
    # 1. Not a floor tile
    # 2. Within safe radius of start
    # 3. Within safe radius of goal
    # 4. Too close to existing spikes
    # 5. Would create a dead end (only 1 floor neighbor)
```

---

### 5. Particle System

Visual effects for collecting items and taking damage.

```mermaid
classDiagram
    class ParticleSystem {
        +list particles
        +add_burst(x, y, color, count)
        +update(delta_time)
        +draw(cam_x, cam_y)
    }
    
    class Particle {
        +float x, y
        +float vx, vy
        +float life
        +tuple color
        +float size
    }
    
    ParticleSystem --> Particle : creates
```

#### Particle Properties ([`main.py:120-154`](main.py:120))

```python
class ParticleSystem:
    def add_burst(self, x, y, color=(255, 255, 100), count=8):
        """Create explosion of particles at position."""
        for _ in range(count):
            self.particles.append({
                "x": x, "y": y,
                "vx": random.uniform(-80, 80),
                "vy": random.uniform(-80, 80),
                "life": 1.0,
                "color": color,
                "size": random.uniform(2, 6)
            })
```

Particle physics:
- Velocity: random direction, -80 to 80 pixels/sec
- Gravity: 300 pixels/sec²
- Life decay: 3 units per second
- Fades out as life decreases

---

### 6. Player System

```mermaid
classDiagram
    class Player {
        +int x, y
        +int last_safe_x, last_safe_y
        +int score
        +bool dead
        +int move_delay
        +int last_move_time
        +int level
        +dict collected
        +move(dx, dy, grid)
    }
    
    class Grid {
        +int WORLD_COLS = 120
        +int WORLD_ROWS = 120
        +Tile types: FLOOR, WALL, SPIKE, TRAP, GOAL
    }
    
    Player --> Grid : moves on
```

#### Player Movement ([`main.py:477-515`](main.py:477))

```python
def move(self, dx, dy, grid):
    # Movement cooldown check (140ms)
    # Boundary checks (0 to WORLD_COLS-1)
    # Wall collision check
    # Handle tile interactions:
    #   - TRAP: Kill player, return "TRAP_DEATH"
    #   - ITEM_TYPES: Add points, play sound, collect
    #   - GOAL: Return "NEXT" to advance level
```

---

### 7. Camera System

Smooth scrolling camera that follows the player.

```mermaid
flowchart TD
    A[get_camera] --> B[Calculate Target Position]
    B --> C[target_x = player.x * TILE_SIZE - SCREEN_WIDTH // 2]
    C --> D[target_y = player.y * TILE_SIZE - SCREEN_HEIGHT // 2]
    D --> E[Lerp Camera]
    E --> F["camera_x += (target_x - camera_x) * 0.12"]
    F --> G["camera_y += (target_y - camera_y) * 0.12"]
    G --> H[Return camera position]
```

#### Camera Implementation ([`main.py:524-530`](main.py:524))

```python
def get_camera(player):
    global camera_x, camera_y
    target_x = player.x * TILE_SIZE - SCREEN_WIDTH // 2
    target_y = player.y * TILE_SIZE - SCREEN_HEIGHT // 2
    camera_x += (target_x - camera_x) * 0.12  # Smooth interpolation
    camera_y += (target_y - camera_y) * 0.12
    return int(camera_x), int(camera_y)
```

---

## Game States

The game uses 7 distinct states managed by the main loop.

```mermaid
stateDiagram-v2
    [*] --> SPLASH: Game Start
    SPLASH --> NARRATIVE: Any Key Pressed
    NARRATIVE --> PLAY: Any Key Pressed
    PLAY --> SUMMARY: Goal Reached
    PLAY --> MESSAGE: Lose Life (spike/fireball)
    PLAY --> MESSAGE: Trap (50% climb out)
    PLAY --> FALLING: Trap Death (no lives left)
    SUMMARY --> NARRATIVE: Any Key (Next Level)
    MESSAGE --> PLAY: Message Complete
    FALLING --> GAMEOVER: Animation Complete
    GAMEOVER --> SPLASH: Any Key Restart
    GAMEOVER --> [*]: ESC Pressed
```

### State Definitions

| State | Constant | Description |
|-------|----------|-------------|
| SPLASH | `STATE_SPLASH` | Title screen with ASCII art and player character |
| NARRATIVE | `STATE_NARRATIVE` | Story text between levels |
| PLAY | `STATE_PLAY` | Main gameplay |
| SUMMARY | `STATE_SUMMARY` | Level completion celebration |
| MESSAGE | `STATE_MESSAGE` | Life loss messages with backgrounds |
| FALLING | `STATE_FALLING` | Trap death animation with pit background |
| GAMEOVER | `STATE_GAMEOVER` | Death screen with high scores |

### State Handlers

#### Splash Screen ([`main.py:1146-1195`](main.py:1146))

Displays the player character image alongside ASCII art title:
- **Player Character**: Large playerBig.png displayed on the left side
- **ASCII Title**: Green ASCII art on the right side
- **Version**: Displayed below the title
- **Prompt**: "PRESS ANY KEY TO BEGIN" 

The splash screen now features the full-resolution player character image (800x1280) scaled to fit, creating a more engaging title screen.

#### Narrative Screen ([`main.py:750-817`](main.py:750))

Shows level-specific story text loaded from [`narratives.json`](narratives.json):
- Level title in gold
- Story text in white
- Level number in purple
- Optional background image from assets

#### Level Summary ([`main.py:652-690`](main.py:652))

Celebration screen shown after completing a level:
- "LEVEL COMPLETE!" title with glow effect
- Level number, score gained, total score
- Animated sun graphic with glow rings
- "Press ANY KEY" prompt

#### Death Animation ([`main.py:609-646`](main.py:609))

Spinning spiral animation that creates a "falling into hole" effect:
- Black spiral arcs expanding inward
- Growing black circle in center
- "YOU FELL!" text fading out

---

## Entity Relationships

### Grid Coordinate System

```mermaid
flowchart TB
    subgraph World["World Grid (120x120)"]
        subgraph Region1["Start Area (Safe)"]
            S[Start Position]
        end
        subgraph Region2["Dungeon Rooms"]
            R1[Room 1]
            R2[Room 2]
            R3[Room N...]
        end
        subgraph Region3["Goal Area (Safe)"]
            G[Goal Position]
        end
        
        S -->|Corridor| R1
        R1 -->|Corridor| R2
        R2 -->|Corridor| R3
        R3 -->|Corridor| G
    end
    
    S -.->|Safe Radius 8| S
    G -.->|Safe Radius 8| G
```

### Level Progression

```mermaid
flowchart LR
    subgraph Persistent["Persistent Data"]
        PL[persistent_level]
        PS[persistent_score]
        PC[persistent_collected]
    end
    
    subgraph Level1["Level 1"]
        G1[generate_world]
        P1[place_items]
        T1[place_traps]
        S1[spike_system.generate_spikes]
        Play1[Play]
        Result1{Win/Lose?}
    end
    
    subgraph LevelN["Level N"]
        G2[generate_world]
        P2[place_items]
        T2[place_traps]
        S2[spike_system.generate_spikes]
        Play2[Play]
    end
    
    PL --> G1
    PS --> P1
    PC --> P1
    Result1 -->|Win| PL[persistent_level += 1]
    Result1 -->|Lose| Reset[Reset to Level 1]
```

---

## Main Game Loop

The main loop runs at 60 FPS and handles all game logic.

```mermaid
flowchart TD
    A[Main Loop<br/>while True] --> B["clock.tick(FPS)"]
    B --> C[Calculate delta_time]
    C --> D{Event Processing}
    D --> E[QUIT Event]
    E -->|Yes| F["pygame.quit() & sys.exit()"]
    E -->|No| G{KEYDOWN Event}
    
    G -->|STATE_SPLASH| H[Initialize Game]
    G -->|STATE_SUMMARY| I[Next Level++]
    G -->|STATE_NARRATIVE| J[start_level]
    G -->|STATE_GAMEOVER| K[Reset to Splash]
    
    H --> L{State Machine}
    I --> L
    J --> L
    
    L -->|STATE_SPLASH| M[draw_splash]
    L -->|STATE_NARRATIVE| N[draw_narrative]
    L -->|STATE_PLAY| O[Gameplay Update]
    L -->|STATE_SUMMARY| P[draw_level_summary]
    L -->|STATE_FALLING| Q[draw_fall_transition]
    L -->|STATE_GAMEOVER| R[draw_gameover]
    
    M --> S[pygame.display.flip]
    N --> S
    O --> T[Update Entities]
    T --> U[Update Spikes]
    U --> V[Update Particles]
    V --> W[Player Input]
    W --> X[Player Move]
    X --> Y{Hit Detection}
    Y -->|Spike| Z[Death]
    Y -->|Trap| AA[Falling]
    Y -->|Goal| BB[Level Complete]
    Y -->|None| S
    
    S --> A
```

### Main Loop Implementation ([`main.py:938-1074`](main.py:938))

```python
while True:
    clock.tick(FPS)
    current_time = pygame.time.get_ticks()
    delta_time = (current_time - last_time) / 1000.0
    last_time = current_time

    for event in pygame.event.get():
        # Handle all game events
        if event.type == SONG_FINISHED:
            play_next_song()
        # ... state-specific key handling

    # State-based rendering and logic
    if state == STATE_PLAY:
        # Update systems
        particles.update(delta_time)
        player.dead = spike_system.update(delta_time, player.x, player.y, particles)
        # Handle input
        # Check collisions
        # Render
    
    pygame.display.flip()
```

---

### 8. Health and Lives System

Players now have a health and lives system that adds strategy to hazard encounters.

#### Health System

- **Health Calculation**: Health = 50% of current score (dynamically calculated)
- **Health Cap**: Maximum health is 100,000
- **Spike Damage**: 20 health points per spike hit
- **Fireball Damage**: 25 health points per fireball hit
- **Death Condition**: When health drops to 0 or below, player loses a life

#### Lives System

- **Starting Lives**: 5 lives at game start
- **Extra Lives**: Earn +1 life for every 250,000 points
- **On Life Loss**:
  - Score resets to 0
  - All collected items are lost
  - Level progression is maintained
  - "You lost a life!" message displayed
- **Game Over**: Only triggers when lives reach 0

#### Trap/Hole Mechanics

When falling into a trap (hole):
- 50% chance to climb out and survive
- 50% chance to lose a life
- Messages displayed: "You climbed out!" or "You lost a life!"

#### Message Screens

Life loss events show themed backgrounds:
- `LIFE_LOSS_BG_FILES` - Backgrounds for life loss messages
- `FALL_BG_FILES` - Backgrounds for falling animation (e.g., pit.jpg)

---

### 9. Fireball System

Fireballs are projectile hazards that travel across corridors.

```mermaid
flowchart TD
    A[FireballSystem.generate_fireballs] --> B[Find Corridors]
    B --> C{Corridor >= 6 tiles?}
    C -->|No| B
    C -->|Yes| D{Adjacent to Wall?}
    D -->|No| B
    D -->|Yes| E{Random < FIREBALL_PROFUSION?}
    E -->|Yes| F[Create Fireball]
    E -->|No| B
    
    G[FireballSystem.update] --> H[Update Phase]
    H --> I{Calculate Position}
    I --> J{"sin(phase) determines extend"}
    J --> K{Fireball Extended?}
    K -->|Yes| L{Check Player Collision}
    K -->|No| M[Reset Hit Flag]
    L -->|Hit| N[Return hit = True]
```

#### Fireball Properties

- **Spawn**: Corridors of 6+ tiles adjacent to walls
- **Movement**: Emerge from wall, travel across, disappear into opposite wall
- **Cycle**: Uses sine wave for extend/retract (like spikes)
- **Collision**: Only damages player when extended (50%+ progress)
- **Configurable**: `FIREBALL_PROFUSION`, `FIREBALL_DAMAGE`, `FIREBALL_SPEED`

---

## UI Components

### Stats Bar ([`main.py:173-211`](main.py:173))

Displays at the top of the screen during gameplay:
- Current level number
- Total score
- Collected item counts with icons

### Minimap ([`main.py:553-562`](main.py:553))

200x200 pixel map in the top-right corner:
- Gray dots for floor tiles
- Red dot for player position

### Torch Effect ([`main.py:546-551`](main.py:546))

Darkness overlay creating a "torch lit" atmosphere:
- Semi-transparent black overlay (alpha 220)
- Clear circle around player (200px radius)

---

## Audio System

### Sound Effects

| Sound | Trigger | File |
|-------|---------|------|
| Spike hit | Player touched by spike | spikehit.mp3 |
| Item pickup | Collect any item | coin.wav |
| Spike extend | Spike starts extending | spike_extend.wav |
| Level win | Reach goal tile | win.wav |
| Trap fall | Step on trap | fall.mp3 |
| Extra life | Earn bonus life | extra_life.mp3 |

### Music System

- Playlist of 9 audio files
- Random selection on each song end
- Volume: 50%

---

## File Dependencies

```mermaid
flowchart TD
    main.py --> narratives.json
    main.py --> highscores.txt
    main.py --> assets/
    
    assets --> floor.png
    assets --> wall.png
    assets --> spike.png
    assets --> sun.png
    assets --> player.png
    assets --> coin.png
    assets --> mushroom.png
    assets --> trophy.png
    assets --> poison.png
    assets --> coins.png
    assets --> gem10k.png
    assets --> gem80ka.png
    assets --> gem80kb.png
    assets --> gem80kc.png
    assets --> gem100k.png
    
    assets --> music.mp3
    assets --> 01.ogg
    assets --> 02.ogg
    assets --> 03.ogg
    assets --> 04.ogg
    assets --> 05.ogg
    assets --> 06.ogg
    assets --> 07.ogg
    assets --> 08.ogg
    
    assets --> coin.wav
    assets --> hit.wav
    assets --> spike_extend.wav
    assets --> win.wav
    assets --> trap_fall.wav
    
    assets --> narrative_01.jpg
    assets --> narrative_02.png
    assets --> narrative_03.png
    
    assets --> fireball.png
    assets --> playerBig.png
    assets --> pit.jpg
    assets --> lostlife.png
    
    assets --> spikehit.mp3
    assets --> fall.mp3
    assets --> extra_life.mp3
```

---

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Move player |
| Any Key | Advance screens |
| ESC | Quit game |

---

## Technical Notes

### Performance Considerations

1. **Viewport Culling**: Only tiles visible on screen are rendered ([`main.py:571`](main.py:571))
2. **Delta Time**: All physics use delta_time for frame-rate independence
3. **Object Pooling**: Particles are reused rather than recreated

### Color Palette

| Color | RGB | Usage |
|-------|-----|-------|
| GOLD | (255, 215, 0) | Score, titles |
| SUN | (255, 223, 0) | Sun graphics |
| GREEN | (0, 255, 100) | Success messages |
| BLUE | (100, 200, 255) | UI elements |
| PURPLE | (200, 100, 255) | Level numbers |
| RED | (255, 100, 100) | Warnings, poison |

---

*Documentation generated for Bruce's Treasure v1.1*

## Changelog v1.1

### New Features
- Health and Lives system
- Fireball hazards
- Enhanced splash screen with player character
- Message screens with themed backgrounds
- Extra life bonus every 250k points

### Changes
- Spikes now deal damage instead of instant death
- Traps have 50% chance to climb out
- Game over only when lives reach 0
- Health capped at 100,000
