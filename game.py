"""
Features:

🚀 Spaceship movement
☄️ Random falling asteroids
❤️ 3 lives
⭐ Score system
📈 Increasing difficulty/levels
⏸️ Pause with P
🔄 Restart with R
⌨️ Move with ← → or A / D
🖥️ Uses Python's built-in tkinter, so no external game library is required.
"""


import tkinter as tk
import random

# =========================
# SPACE DODGER - Python Game
# =========================

WIDTH = 800
HEIGHT = 600
PLAYER_SPEED = 9
STARTING_LIVES = 3

root = tk.Tk()
root.title("🚀 Space Dodger")
root.resizable(False, False)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#050816", highlightthickness=0)
canvas.pack()

# Game state
score = 0
lives = STARTING_LIVES
level = 1
running = False
paused = False
keys = set()
asteroids = []
stars = []

# ---------- Background ----------
for _ in range(90):
    x = random.randint(0, WIDTH)
    y = random.randint(0, HEIGHT)
    r = random.choice([1, 1, 1, 2])
    star = canvas.create_oval(x-r, y-r, x+r, y+r, fill="white", outline="")
    stars.append([star, random.uniform(0.5, 2.0)])

# ---------- Player ----------
player_x = WIDTH // 2
player_y = HEIGHT - 75
player = None
player_shield = None

def create_player():
    global player, player_shield
    canvas.delete("player")
    player = canvas.create_polygon(
        player_x, player_y - 28,
        player_x - 22, player_y + 25,
        player_x, player_y + 14,
        player_x + 22, player_y + 25,
        fill="#35d9ff",
        outline="#ffffff",
        width=2,
        tags="player"
    )
    player_shield = canvas.create_oval(
        player_x - 30, player_y - 36,
        player_x + 30, player_y + 36,
        outline="#2563eb",
        width=2,
        tags="player"
    )

# ---------- HUD ----------
hud = canvas.create_text(
    20, 20, anchor="nw",
    fill="white", font=("Arial", 18, "bold"),
    text=""
)

message = canvas.create_text(
    WIDTH // 2, HEIGHT // 2,
    fill="white", font=("Arial", 28, "bold"),
    text=""
)

def update_hud():
    canvas.itemconfig(
        hud,
        text=f"Score: {score}    ❤️ Lives: {lives}    ⭐ Level: {level}"
    )

# ---------- Asteroids ----------
def spawn_asteroid():
    if not running or paused:
        return

    size = random.randint(18, 38)
    x = random.randint(size, WIDTH - size)
    y = -size
    speed = random.uniform(3.0 + level * 0.45, 5.0 + level * 0.55)

    asteroid = canvas.create_oval(
        x-size, y-size, x+size, y+size,
        fill=random.choice(["#6b7280", "#9ca3af", "#4b5563"]),
        outline="#d1d5db",
        width=2,
        tags="asteroid"
    )

    asteroids.append([asteroid, x, y, size, speed])

    delay = max(180, 750 - level * 55)
    root.after(delay, spawn_asteroid)

def move_asteroids():
    global score, lives, level

    if not running:
        return

    if not paused:
        for a in asteroids[:]:
            obj, x, y, size, speed = a
            y += speed
            a[2] = y

            canvas.move(obj, 0, speed)

            # Collision with player
            if abs(x - player_x) < size + 20 and abs(y - player_y) < size + 28:
                canvas.delete(obj)
                asteroids.remove(a)
                lives -= 1
                update_hud()

                if lives <= 0:
                    game_over()
                    return

            # Missed asteroid
            elif y - size > HEIGHT:
                canvas.delete(obj)
                asteroids.remove(a)
                score += 10
                level = score // 100 + 1
                update_hud()

    root.after(25, move_asteroids)

def move_stars():
    for star, speed in stars:
        canvas.move(star, 0, speed)
        coords = canvas.coords(star)
        if coords and coords[1] > HEIGHT:
            x = random.randint(0, WIDTH)
            canvas.coords(star, x, 0, x+2, 2)

    if running:
        root.after(40, move_stars)

# ---------- Controls ----------
def key_down(event):
    keys.add(event.keysym.lower())

    if event.keysym.lower() == "p" and running:
        toggle_pause()

    if event.keysym.lower() == "r" and not running:
        start_game()

def key_up(event):
    keys.discard(event.keysym.lower())

def move_player():
    global player_x

    if running and not paused:
        if "left" in keys or "a" in keys:
            player_x -= PLAYER_SPEED
        if "right" in keys or "d" in keys:
            player_x += PLAYER_SPEED

        player_x = max(35, min(WIDTH - 35, player_x))

        # Move both player shapes together
        canvas.coords(
            player,
            player_x, player_y - 28,
            player_x - 22, player_y + 25,
            player_x, player_y + 14,
            player_x + 22, player_y + 25
        )
        canvas.coords(
            player_shield,
            player_x - 30, player_y - 36,
            player_x + 30, player_y + 36
        )

    root.after(20, move_player)

# ---------- Game control ----------
def start_game():
    global score, lives, level, running, paused, player_x, asteroids

    for a in asteroids:
        canvas.delete(a[0])
    asteroids.clear()

    score = 0
    lives = STARTING_LIVES
    level = 1
    player_x = WIDTH // 2
    running = True
    paused = False

    canvas.itemconfig(message, text="")
    create_player()
    update_hud()

    spawn_asteroid()

def toggle_pause():
    global paused
    paused = not paused
    canvas.itemconfig(message, text="PAUSED\nPress P to continue" if paused else "")

def game_over():
    global running
    running = False
    canvas.itemconfig(
        message,
        text=f"GAME OVER\n\nScore: {score}\n\nPress R to play again"
    )

# ---------- Start screen ----------
create_player()
canvas.itemconfig(
    message,
    text="🚀 SPACE DODGER 🚀\n\n"
         "Move: ← → or A / D\n"
         "Pause: P\n\n"
         "Avoid the asteroids!\n"
         "Press ENTER to start"
)

def start_from_enter(event):
    if not running:
        start_game()

root.bind("<KeyPress>", key_down)
root.bind("<KeyRelease>", key_up)
root.bind("<Return>", start_from_enter)

move_player()
move_stars()

root.mainloop()
