import tkinter as tk
import random
import math
import json
from pathlib import Path

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
WIDTH, HEIGHT = 900, 650
BASE_FPS = 15
PLAYER_SPEED = 7.2
MAX_LIVES = 3
HIGH_SCORE_FILE = Path.home() / ".neon_galaxy_highscore.json"

# Neon palette
NEON_CYAN   = "#22d3ee"
NEON_PINK   = "#f472b6"
NEON_PURPLE = "#c084fc"
NEON_YELLOW = "#fde047"
NEON_ORANGE = "#fb923c"
NEON_GREEN  = "#4ade80"
DARK_BG     = "#030712"

root = tk.Tk()
root.title("NEON GALAXY 🚀")
root.resizable(False, False)
root.configure(bg=DARK_BG)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                   bg=DARK_BG, highlightthickness=0)
canvas.pack()

# ────────────────────────────────────────────────
# STATE
# ────────────────────────────────────────────────
screen = "menu"
score = 0
level = 1
lives = MAX_LIVES
high_score = 0
paused = False
player_x = WIDTH // 2
player_y = HEIGHT - 95
keys = set()

asteroids = []
bullets = []
enemy_bullets = []
powerups = []
particles = []
stars = []
bullet_trails = []

boss = None
boss_active = False
boss_hp = boss_max_hp = 0

spawn_timer = 18
shoot_cooldown = 0
invincible_timer = 0
time_scale = 1.0
time_warp_timer = 0
combo = 0
combo_timer = 0
frame = 0

try:
    high_score = int(json.loads(HIGH_SCORE_FILE.read_text()).get("high_score", 0))
except Exception:
    high_score = 0

# ────────────────────────────────────────────────
# BACKGROUND – multi-layer neon stars + scanlines
# ────────────────────────────────────────────────
for _ in range(90):
    x, y = random.randrange(WIDTH), random.randrange(HEIGHT)
    s = random.choice([1, 1, 2])
    color = random.choice(["#94a3b8", "#67e8f9", "#c4b5fd", "#f0abfc"])
    stars.append([
        canvas.create_oval(x, y, x+s, y+s, fill=color, outline=""),
        random.uniform(0.3, 1.1), s
    ])
for _ in range(50):
    x, y = random.randrange(WIDTH), random.randrange(HEIGHT)
    s = random.choice([2, 3])
    color = random.choice(["#22d3ee", "#a78bfa", "#f472b6"])
    stars.append([
        canvas.create_oval(x, y, x+s, y+s, fill=color, outline=""),
        random.uniform(1.2, 2.6), s
    ])

# Soft vignette (dark edges)
vignette = [
    canvas.create_rectangle(0, 0, WIDTH, 40, fill="#000000", outline="", stipple="gray50"),
    canvas.create_rectangle(0, HEIGHT-50, WIDTH, HEIGHT, fill="#000000", outline="", stipple="gray50"),
]

# Subtle horizontal scanlines
scanlines = []
for y in range(0, HEIGHT, 4):
    scanlines.append(
        canvas.create_line(0, y, WIDTH, y, fill="#0f172a", width=1)
    )

# ────────────────────────────────────────────────
# UI ELEMENTS
# ────────────────────────────────────────────────
hud = canvas.create_text(20, 16, anchor="nw", fill="#e2e8f0",
                         font=("Consolas", 15, "bold"))
level_text = canvas.create_text(WIDTH-20, 16, anchor="ne", fill=NEON_CYAN,
                                font=("Consolas", 15, "bold"))
speed_text = canvas.create_text(WIDTH//2, 16, anchor="n", fill=NEON_YELLOW,
                                font=("Consolas", 13, "bold"))
combo_text = canvas.create_text(WIDTH//2, 48, anchor="n", fill=NEON_PINK,
                                font=("Consolas", 18, "bold"))

boss_bg = canvas.create_rectangle(220, 58, 680, 74,
                                  fill="#1e1b4b", outline="", state="hidden")
boss_bar = canvas.create_rectangle(220, 58, 680, 74,
                                   fill=NEON_PINK, outline="", state="hidden")
boss_label = canvas.create_text(WIDTH//2, 48, text="◆ BOSS ◆",
                                fill=NEON_PURPLE, font=("Consolas", 12, "bold"),
                                state="hidden")

title = canvas.create_text(WIDTH//2, 140, text="NEON GALAXY",
                           fill=NEON_CYAN, font=("Consolas", 48, "bold"))
subtitle = canvas.create_text(WIDTH//2, 195, text="▸ SPACE SURVIVAL ◂",
                              fill=NEON_PURPLE, font=("Consolas", 16, "bold"))
menu = canvas.create_text(WIDTH//2, 340, fill="#e2e8f0",
                          font=("Consolas", 15), justify="center")
message = canvas.create_text(WIDTH//2, HEIGHT//2, fill="white",
                             font=("Consolas", 28, "bold"), justify="center")

player_parts = []

# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def distance(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)

def burst(x, y, color=NEON_CYAN, amount=16, speed_mult=1.0):
    for _ in range(amount):
        a = random.random() * math.tau
        sp = random.uniform(1.8, 7.5) * speed_mult * time_scale
        size = random.randint(2, 4)
        item = canvas.create_oval(x-size, y-size, x+size, y+size,
                                  fill=color, outline="")
        particles.append([item, x, y, math.cos(a)*sp, math.sin(a)*sp,
                          random.randint(12, 32)])

def update_particles():
    for p in particles[:]:
        item, x, y, vx, vy, life = p
        x += vx
        y += vy
        vx *= 0.96
        vy *= 0.96
        life -= 1
        p[1:6] = [x, y, vx, vy, life]
        s = max(1, life // 8)
        canvas.coords(item, x-s, y-s, x+s, y+s)
        if life <= 0:
            canvas.delete(item)
            particles.remove(p)

def update_trails():
    for t in bullet_trails[:]:
        item, life = t
        life -= 1
        t[1] = life
        if life <= 0:
            canvas.delete(item)
            bullet_trails.remove(t)
        else:
            # fade by reducing size slightly
            coords = canvas.coords(item)
            if coords:
                cx = (coords[0] + coords[2]) / 2
                cy = (coords[1] + coords[3]) / 2
                s = max(1, life / 6)
                canvas.coords(item, cx-s, cy-s, cx+s, cy+s)

# ────────────────────────────────────────────────
# PLAYER
# ────────────────────────────────────────────────
def draw_player():
    for item in player_parts:
        canvas.delete(item)
    player_parts.clear()

    pulse = 1.0
    if invincible_timer:
        pulse = 1.0 + 0.18 * math.sin(frame * 0.35)

    # Outer glow
    g = 38 * pulse
    glow = canvas.create_oval(player_x-g, player_y-g, player_x+g, player_y+g,
                              outline="#0e7490", width=2)
    # Inner glow
    g2 = 28 * pulse
    glow2 = canvas.create_oval(player_x-g2, player_y-g2, player_x+g2, player_y+g2,
                               outline="#22d3ee", width=1)

    # Ship body
    ship = canvas.create_polygon(
        player_x,       player_y - 36,
        player_x - 26,  player_y + 24,
        player_x - 8,   player_y + 16,
        player_x,       player_y + 32,
        player_x + 8,   player_y + 16,
        player_x + 26,  player_y + 24,
        fill=NEON_CYAN, outline="#ecfeff", width=2
    )

    # Cockpit
    cockpit = canvas.create_oval(player_x-9, player_y-14,
                                 player_x+9, player_y+4,
                                 fill="#0f172a", outline="#a5f3fc", width=2)

    # Side lights
    left_light  = canvas.create_oval(player_x-22, player_y+6, player_x-14, player_y+14,
                                     fill=NEON_PINK, outline="")
    right_light = canvas.create_oval(player_x+14, player_y+6, player_x+22, player_y+14,
                                     fill=NEON_PINK, outline="")

    # Animated thruster
    flame_h = 48 + random.randint(0, 10) + int(4 * time_scale)
    flame = canvas.create_polygon(
        player_x - 10, player_y + 24,
        player_x,      player_y + flame_h,
        player_x + 10, player_y + 24,
        fill=NEON_ORANGE, outline=""
    )
    flame_core = canvas.create_polygon(
        player_x - 5, player_y + 26,
        player_x,     player_y + flame_h - 8,
        player_x + 5, player_y + 26,
        fill=NEON_YELLOW, outline=""
    )

    player_parts.extend([glow, glow2, ship, cockpit, left_light, right_light, flame, flame_core])

# ────────────────────────────────────────────────
# SPAWNERS
# ────────────────────────────────────────────────
def spawn_asteroid():
    size = random.randint(18, 44)
    x = random.randint(size + 15, WIDTH - size - 15)
    y = -size - 10
    speed = random.uniform(2.6 + level * 0.22, 4.8 + level * 0.38) * time_scale

    points = []
    for i in range(11):
        a = i * math.tau / 11
        r = size * random.uniform(0.75, 1.18)
        points += [x + math.cos(a) * r, y + math.sin(a) * r]

    # Neon outline asteroids
    item = canvas.create_polygon(
        *points,
        fill=random.choice(["#1e293b", "#334155", "#0f172a"]),
        outline=random.choice(["#67e8f9", "#a5b4fc", "#c4b5fd"]),
        width=2
    )
    asteroids.append({
        "item": item, "x": x, "y": y, "size": size,
        "speed": speed, "hp": 1 if size < 30 else 2
    })

def shoot():
    global shoot_cooldown
    if shoot_cooldown > 0:
        return

    speed = 14 * time_scale
    for dx in (-12, 12):
        # Main bullet
        item = canvas.create_rectangle(
            player_x + dx - 2.5, player_y - 40,
            player_x + dx + 2.5, player_y - 18,
            fill=NEON_YELLOW, outline="#fffbeb", width=1
        )
        bullets.append({"item": item, "x": player_x + dx, "y": player_y - 30, "speed": speed})

        # Trail particle
        trail = canvas.create_oval(player_x+dx-3, player_y-28, player_x+dx+3, player_y-22,
                                   fill="#fef08a", outline="")
        bullet_trails.append([trail, 8])

    burst(player_x, player_y - 34, NEON_YELLOW, 6, 0.7)
    shoot_cooldown = max(3, int(6.5 / time_scale))

def spawn_powerup(x, y):
    kind = random.choices(
        ["life", "rapid", "shield", "warp"],
        weights=[18, 28, 28, 26]
    )[0]
    colors  = {"life": NEON_PINK, "rapid": NEON_YELLOW, "shield": "#38bdf8", "warp": NEON_PURPLE}
    symbols = {"life": "♥", "rapid": "⚡", "shield": "◆", "warp": "⌛"}

    # Outer glow ring
    glow = canvas.create_oval(x-18, y-18, x+18, y+18,
                              outline=colors[kind], width=2)
    item = canvas.create_oval(x-13, y-13, x+13, y+13,
                              fill=colors[kind], outline="white", width=1)
    label = canvas.create_text(x, y, text=symbols[kind],
                               fill="#0f172a", font=("Arial", 12, "bold"))
    powerups.append({
        "item": item, "label": label, "glow": glow,
        "x": x, "y": y, "kind": kind
    })

# ────────────────────────────────────────────────
# COMBAT & BOSS
# ────────────────────────────────────────────────
def hit_player():
    global lives, invincible_timer, combo
    if invincible_timer > 0:
        return
    lives -= 1
    invincible_timer = 85
    combo = 0
    burst(player_x, player_y, NEON_PINK, 40, 1.3)
    hud_update()
    if lives <= 0:
        end_game()

def start_boss():
    global boss_active, boss_hp, boss_max_hp, boss
    boss_active = True
    boss_max_hp = 110 + level * 32
    boss_hp = boss_max_hp

    x, y = WIDTH // 2, -90
    body = canvas.create_polygon(
        x, y-65,
        x-90, y-20,
        x-120, y+50,
        x-50, y+35,
        x, y+70,
        x+50, y+35,
        x+120, y+50,
        x+90, y-20,
        fill="#4c1d95", outline=NEON_PURPLE, width=3
    )
    # Glowing core
    core = canvas.create_oval(x-28, y-8, x+28, y+38,
                              fill=NEON_PINK, outline="#fecdd3", width=2)
    eye = canvas.create_oval(x-12, y+4, x+12, y+28,
                             fill="#0f172a", outline="")

    boss = {"body": body, "core": core, "eye": eye, "x": x, "y": y, "vx": 3.2 * time_scale}

    canvas.itemconfig(boss_bg, state="normal")
    canvas.itemconfig(boss_bar, state="normal")
    canvas.itemconfig(boss_label, state="normal")
    boss_shoot()

def boss_shoot():
    if not boss_active or boss is None or paused:
        return
    for dx in (-60, -20, 20, 60):
        item = canvas.create_oval(
            boss["x"]+dx-7, boss["y"]+42,
            boss["x"]+dx+7, boss["y"]+56,
            fill=NEON_PINK, outline="#fff1f2"
        )
        enemy_bullets.append({
            "item": item,
            "x": boss["x"] + dx,
            "y": boss["y"] + 50,
            "vx": dx * 0.018 * time_scale,
            "vy": (5.2 + level * 0.18) * time_scale
        })
    delay = max(260, int((850 - level * 18) / time_scale))
    root.after(delay, boss_shoot)

def defeat_boss():
    global boss_active, boss, score
    burst(boss["x"], boss["y"], NEON_PURPLE, 110, 1.6)
    score += 1200 + level * 50
    for key in ("body", "core", "eye"):
        canvas.delete(boss[key])
    boss = None
    boss_active = False
    canvas.itemconfig(boss_bg, state="hidden")
    canvas.itemconfig(boss_bar, state="hidden")
    canvas.itemconfig(boss_label, state="hidden")

def activate_powerup(kind):
    global lives, invincible_timer, time_warp_timer, shoot_cooldown
    if kind == "life":
        lives = min(MAX_LIVES, lives + 1)
        burst(player_x, player_y, NEON_PINK, 20)
    elif kind == "rapid":
        shoot_cooldown = 0
        invincible_timer = max(invincible_timer, 40)
    elif kind == "shield":
        invincible_timer = 320
    elif kind == "warp":
        time_warp_timer = 300
        burst(player_x, player_y, NEON_PURPLE, 30)
    hud_update()

# ────────────────────────────────────────────────
# HUD & TIME SCALE
# ────────────────────────────────────────────────
def hud_update():
    global high_score
    high_score = max(high_score, score)
    hearts = "♥ " * lives + "♡ " * (MAX_LIVES - lives)
    canvas.itemconfig(hud, text=f"SCORE  {score:06d}   BEST  {high_score:06d}\nLIVES  {hearts}")
    canvas.itemconfig(level_text, text=f"LEVEL {level}")

    warp = "  ⚡ WARP" if time_warp_timer > 0 else ""
    canvas.itemconfig(speed_text, text=f"SPEED ×{time_scale:.2f}{warp}")

    if combo >= 3:
        canvas.itemconfig(combo_text, text=f"COMBO ×{combo}", fill=NEON_PINK)
    else:
        canvas.itemconfig(combo_text, text="")

def update_time_scale():
    global time_scale
    base = 1.0 + min(1.9, (level - 1) * 0.065 + score / 14000)
    time_scale = base * 1.48 if time_warp_timer > 0 else base

# ────────────────────────────────────────────────
# MAIN LOOP
# ────────────────────────────────────────────────
def game_loop():
    global player_x, score, level, spawn_timer, shoot_cooldown
    global invincible_timer, boss_hp, time_warp_timer, combo, combo_timer, frame

    frame += 1

    if screen == "game" and not paused:
        update_time_scale()

        # Movement
        move = PLAYER_SPEED * time_scale
        if "left" in keys or "a" in keys:
            player_x -= move
        if "right" in keys or "d" in keys:
            player_x += move
        player_x = max(42, min(WIDTH - 42, player_x))

        if "space" in keys:
            shoot()
        if shoot_cooldown > 0:
            shoot_cooldown -= 1

        draw_player()

        # Spawn
        spawn_timer -= time_scale
        if spawn_timer <= 0 and not boss_active:
            spawn_asteroid()
            spawn_timer = max(9, (42 - level * 1.8) / time_scale)

        # Level up
        new_level = score // 480 + 1
        if new_level > level:
            level = new_level
            burst(WIDTH // 2, HEIGHT // 2, NEON_CYAN, 55)
            if level % 5 == 0 and not boss_active:
                start_boss()

        # Asteroids
        for a in asteroids[:]:
            a["y"] += a["speed"]
            canvas.move(a["item"], 0, a["speed"])
            if a["y"] - a["size"] > HEIGHT + 20:
                canvas.delete(a["item"])
                asteroids.remove(a)
                score += 4
                continue
            if distance(a["x"], a["y"], player_x, player_y) < a["size"] + 26:
                canvas.delete(a["item"])
                asteroids.remove(a)
                burst(a["x"], a["y"], NEON_ORANGE, 28)
                hit_player()

        # Player bullets
        for b in bullets[:]:
            b["y"] -= b["speed"]
            canvas.move(b["item"], 0, -b["speed"])
            if b["y"] < -30:
                canvas.delete(b["item"])
                bullets.remove(b)
                continue

            hit = False
            for a in asteroids[:]:
                if distance(b["x"], b["y"], a["x"], a["y"]) < a["size"] + 6:
                    a["hp"] -= 1
                    burst(b["x"], b["y"], NEON_YELLOW, 8)
                    canvas.delete(b["item"])
                    bullets.remove(b)
                    hit = True
                    combo += 1
                    combo_timer = 90
                    if a["hp"] <= 0:
                        pts = (28 + a["size"] // 2) * (1 + combo // 5)
                        score += pts
                        burst(a["x"], a["y"], "#94a3b8", 26)
                        if random.random() < 0.11:
                            spawn_powerup(a["x"], a["y"])
                        canvas.delete(a["item"])
                        asteroids.remove(a)
                    break

            if not hit and boss_active and boss:
                if distance(b["x"], b["y"], boss["x"], boss["y"]) < 100:
                    boss_hp -= 1
                    burst(b["x"], b["y"], NEON_PURPLE, 5)
                    canvas.delete(b["item"])
                    bullets.remove(b)
                    ratio = max(0, boss_hp / boss_max_hp)
                    canvas.coords(boss_bar, 220, 58, 220 + 460 * ratio, 74)
                    if boss_hp <= 0:
                        defeat_boss()

        # Enemy bullets
        for b in enemy_bullets[:]:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            canvas.move(b["item"], b["vx"], b["vy"])
            if b["y"] > HEIGHT + 30:
                canvas.delete(b["item"])
                enemy_bullets.remove(b)
                continue
            if distance(b["x"], b["y"], player_x, player_y) < 26:
                canvas.delete(b["item"])
                enemy_bullets.remove(b)
                hit_player()

        # Boss movement
        if boss_active and boss:
            if boss["y"] < 115:
                dy = 2.2 * time_scale
                boss["y"] += dy
                for key in ("body", "core", "eye"):
                    canvas.move(boss[key], 0, dy)
            else:
                boss["x"] += boss["vx"]
                if boss["x"] < 130 or boss["x"] > WIDTH - 130:
                    boss["vx"] *= -1
                for key in ("body", "core", "eye"):
                    canvas.move(boss[key], boss["vx"], 0)

        # Power-ups
        for p in powerups[:]:
            dy = 2.4 * time_scale
            p["y"] += dy
            canvas.move(p["item"], 0, dy)
            canvas.move(p["label"], 0, dy)
            canvas.move(p["glow"], 0, dy)
            if p["y"] > HEIGHT + 25:
                canvas.delete(p["item"])
                canvas.delete(p["label"])
                canvas.delete(p["glow"])
                powerups.remove(p)
                continue
            if distance(p["x"], p["y"], player_x, player_y) < 34:
                activate_powerup(p["kind"])
                burst(p["x"], p["y"], NEON_YELLOW, 18)
                canvas.delete(p["item"])
                canvas.delete(p["label"])
                canvas.delete(p["glow"])
                powerups.remove(p)

        # Timers
        if invincible_timer > 0:
            invincible_timer -= 1
        if time_warp_timer > 0:
            time_warp_timer -= 1
        if combo_timer > 0:
            combo_timer -= 1
            if combo_timer <= 0:
                combo = 0

        hud_update()

    update_particles()
    update_trails()

    # Slightly faster frames as speed increases
    delay = max(8, int(BASE_FPS / (0.82 + 0.18 * time_scale)))
    root.after(delay, game_loop)

# ────────────────────────────────────────────────
# STATE MANAGEMENT
# ────────────────────────────────────────────────
def clear_objects():
    for a in asteroids:
        canvas.delete(a["item"])
    for b in bullets:
        canvas.delete(b["item"])
    for b in enemy_bullets:
        canvas.delete(b["item"])
    for p in powerups:
        canvas.delete(p["item"])
        canvas.delete(p["label"])
        canvas.delete(p["glow"])
    for p in particles:
        canvas.delete(p[0])
    for t in bullet_trails:
        canvas.delete(t[0])
    asteroids.clear()
    bullets.clear()
    enemy_bullets.clear()
    powerups.clear()
    particles.clear()
    bullet_trails.clear()

def start_game():
    global screen, score, level, lives, paused, player_x
    global spawn_timer, boss, boss_active, shoot_cooldown
    global invincible_timer, time_scale, time_warp_timer, combo

    clear_objects()
    if boss:
        for key in ("body", "core", "eye"):
            canvas.delete(boss[key])
    boss = None
    boss_active = False
    canvas.itemconfig(boss_bg, state="hidden")
    canvas.itemconfig(boss_bar, state="hidden")
    canvas.itemconfig(boss_label, state="hidden")

    score = 0
    level = 1
    lives = MAX_LIVES
    paused = False
    player_x = WIDTH // 2
    spawn_timer = 18
    shoot_cooldown = 0
    invincible_timer = 0
    time_scale = 1.0
    time_warp_timer = 0
    combo = 0
    screen = "game"

    canvas.itemconfig(title, state="hidden")
    canvas.itemconfig(subtitle, state="hidden")
    canvas.itemconfig(menu, state="hidden")
    canvas.itemconfig(message, text="")
    draw_player()
    hud_update()

def show_menu():
    global screen, paused
    screen = "menu"
    paused = False
    canvas.itemconfig(title, state="normal")
    canvas.itemconfig(subtitle, state="normal")
    canvas.itemconfig(menu, state="normal")
    canvas.itemconfig(menu, text=
        "DODGE  •  SHOOT  •  SURVIVE\n\n"
        "← →   or   A D      Move\n"
        "SPACE                 Shoot\n"
        "P                     Pause\n\n"
        "Press  ENTER  to Start\n\n"
        f"BEST SCORE  {high_score}\n\n"
        "Speed & intensity rise the longer you last")
    canvas.itemconfig(message, text="")

def pause_game():
    global paused
    if screen == "game":
        paused = not paused
        canvas.itemconfig(message,
            text="PAUSED\n\nPress P to continue" if paused else "")

def end_game():
    global screen, high_score
    screen = "gameover"
    if score > high_score:
        high_score = score
        try:
            HIGH_SCORE_FILE.write_text(json.dumps({"high_score": high_score}))
        except Exception:
            pass
    canvas.itemconfig(message, text=
        f"GAME OVER\n\n"
        f"SCORE   {score}\n"
        f"LEVEL   {level}\n"
        f"BEST    {high_score}\n\n"
        "ENTER  →  Play Again\n"
        "ESC    →  Menu")

def key_down(event):
    key = event.keysym.lower()
    keys.add(key)
    if key == "return" and screen in ("menu", "gameover"):
        start_game()
    elif key == "p":
        pause_game()
    elif key == "escape" and screen == "game":
        show_menu()

def key_up(event):
    keys.discard(event.keysym.lower())

def animate_stars():
    for item, speed, size in stars:
        canvas.move(item, 0, speed * max(0.7, time_scale * 0.9))
        c = canvas.coords(item)
        if c and c[1] > HEIGHT:
            x = random.randrange(WIDTH)
            canvas.coords(item, x, -size, x + size, 0)
    root.after(32, animate_stars)

# ────────────────────────────────────────────────
# START
# ────────────────────────────────────────────────
root.bind("<KeyPress>", key_down)
root.bind("<KeyRelease>", key_up)

show_menu()
animate_stars()
game_loop()
root.mainloop()