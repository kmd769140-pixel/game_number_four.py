import tkinter as tk
import random
import math
import json
from pathlib import Path

WIDTH, HEIGHT = 900, 650
FPS = 16
PLAYER_SPEED = 7
MAX_LIVES = 3
HIGH_SCORE_FILE = Path.home() / ".neon_galaxy_highscore.json"

root = tk.Tk()
root.title("NEON GALAXY 🚀")
root.resizable(False, False)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                   bg="#050816", highlightthickness=0)
canvas.pack()

screen = "menu"
score = 0
level = 1
lives = MAX_LIVES
high_score = 0
paused = False
player_x, player_y = WIDTH // 2, HEIGHT - 90
keys = set()

asteroids, bullets, enemy_bullets = [], [], []
powerups, particles, stars = [], [], []
boss = None
boss_active = False
boss_hp = boss_max_hp = 0
spawn_timer = 20
shoot_cooldown = 0
invincible_timer = 0

try:
    high_score = int(json.loads(HIGH_SCORE_FILE.read_text()).get("high_score", 0))
except Exception:
    high_score = 0

# Background
for _ in range(130):
    x, y = random.randrange(WIDTH), random.randrange(HEIGHT)
    s = random.choice([1, 1, 2, 2, 3])
    stars.append([
        canvas.create_oval(x, y, x+s, y+s,
                           fill=random.choice(["white", "#9bdcff", "#b8c7ff"]),
                           outline=""),
        random.uniform(.4, 2.2), s
    ])

player_parts = []

def draw_player():
    for item in player_parts:
        canvas.delete(item)
    player_parts.clear()

    glow = canvas.create_oval(player_x-36, player_y-36,
                              player_x+36, player_y+36,
                              outline="#164e63", width=2)
    ship = canvas.create_polygon(
        player_x, player_y-34,
        player_x-25, player_y+25,
        player_x-6, player_y+18,
        player_x, player_y+30,
        player_x+6, player_y+18,
        player_x+25, player_y+25,
        fill="#22d3ee", outline="#ecfeff", width=2)
    cockpit = canvas.create_oval(player_x-8, player_y-12,
                                 player_x+8, player_y+5,
                                 fill="#0f172a", outline="#a5f3fc", width=2)
    flame = canvas.create_polygon(
        player_x-9, player_y+22, player_x, player_y+45+random.randint(0,7),
        player_x+9, player_y+22, fill="#f97316", outline="")
    player_parts.extend([glow, ship, cockpit, flame])

hud = canvas.create_text(22, 18, anchor="nw", fill="#e2e8f0",
                         font=("Consolas", 16, "bold"))
level_text = canvas.create_text(WIDTH-22, 18, anchor="ne", fill="#67e8f9",
                                font=("Consolas", 16, "bold"))

boss_bg = canvas.create_rectangle(250, 52, 650, 66,
                                  fill="#1e293b", outline="", state="hidden")
boss_bar = canvas.create_rectangle(250, 52, 650, 66,
                                   fill="#ef4444", outline="", state="hidden")

title = canvas.create_text(WIDTH//2, 145, text="NEON GALAXY",
                           fill="#67e8f9", font=("Consolas", 46, "bold"))
subtitle = canvas.create_text(WIDTH//2, 200, text="SPACE SURVIVAL",
                              fill="#c4b5fd", font=("Consolas", 18, "bold"))
menu = canvas.create_text(WIDTH//2, 345, fill="#e2e8f0",
                          font=("Consolas", 16), justify="center")
message = canvas.create_text(WIDTH//2, HEIGHT//2, fill="white",
                             font=("Consolas", 30, "bold"),
                             justify="center")

def hud_update():
    global high_score
    high_score = max(high_score, score)
    canvas.itemconfig(hud, text=f"SCORE {score:06d}    BEST {high_score:06d}\n"
                                f"LIVES {'♥ '*lives}{'♡ '*(MAX_LIVES-lives)}")
    canvas.itemconfig(level_text, text=f"LEVEL {level}")

def burst(x, y, color="#67e8f9", amount=18):
    for _ in range(amount):
        a = random.random() * math.tau
        sp = random.uniform(1.5, 6)
        item = canvas.create_oval(x-3, y-3, x+3, y+3,
                                  fill=color, outline="")
        particles.append([item, x, y, math.cos(a)*sp, math.sin(a)*sp,
                          random.randint(10, 28)])

def update_particles():
    for p in particles[:]:
        item,x,y,vx,vy,life = p
        x += vx; y += vy; vx *= .97; vy *= .97; life -= 1
        p[1:6] = [x,y,vx,vy,life]
        canvas.coords(item, x-2, y-2, x+2, y+2)
        if life <= 0:
            canvas.delete(item); particles.remove(p)

def spawn_asteroid():
    size = random.randint(18, 42)
    x, y = random.randint(size+10, WIDTH-size-10), -size
    speed = random.uniform(2.8+level*.25, 5+level*.4)
    points = []
    for i in range(10):
        a = i*math.tau/10
        r = size*random.uniform(.78,1.15)
        points += [x+math.cos(a)*r, y+math.sin(a)*r]
    item = canvas.create_polygon(*points,
        fill=random.choice(["#475569","#64748b","#52525b"]),
        outline="#cbd5e1", width=2)
    asteroids.append({"item":item,"x":x,"y":y,"size":size,
                      "speed":speed,"hp":1 if size<28 else 2})

def shoot():
    global shoot_cooldown
    if shoot_cooldown: return
    for dx in (-10,10):
        item = canvas.create_rectangle(player_x+dx-2,player_y-38,
                                       player_x+dx+2,player_y-20,
                                       fill="#fef08a", outline="white")
        bullets.append({"item":item,"x":player_x+dx,
                        "y":player_y-30,"speed":13})
    burst(player_x, player_y-32, "#fef08a", 5)
    shoot_cooldown = 7

def spawn_powerup(x,y):
    kind = random.choice(["life","rapid","shield"])
    colors = {"life":"#fb7185","rapid":"#facc15","shield":"#60a5fa"}
    symbols = {"life":"♥","rapid":"⚡","shield":"◆"}
    item = canvas.create_oval(x-14,y-14,x+14,y+14,
                              fill=colors[kind],outline="white",width=2)
    label = canvas.create_text(x,y,text=symbols[kind],
                               fill="#0f172a",font=("Arial",11,"bold"))
    powerups.append({"item":item,"label":label,"x":x,"y":y,"kind":kind})

def distance(x1,y1,x2,y2):
    return math.hypot(x1-x2,y1-y2)

def hit_player():
    global lives, invincible_timer
    if invincible_timer: return
    lives -= 1
    invincible_timer = 90
    burst(player_x,player_y,"#fb7185",35)
    hud_update()
    if lives <= 0: end_game()

def start_boss():
    global boss_active,boss_hp,boss_max_hp,boss
    boss_active=True
    boss_max_hp=120+level*30
    boss_hp=boss_max_hp
    x,y=WIDTH//2,-80
    body=canvas.create_polygon(x,y-60,x-85,y-15,x-115,y+45,x-45,y+30,
        x,y+65,x+45,y+30,x+115,y+45,x+85,y-15,
        fill="#7c3aed",outline="#e9d5ff",width=3)
    eye=canvas.create_oval(x-22,y-10,x+22,y+34,
                           fill="#ef4444",outline="#fecaca",width=2)
    boss={"body":body,"eye":eye,"x":x,"y":y,"vx":3}
    canvas.itemconfig(boss_bg,state="normal")
    canvas.itemconfig(boss_bar,state="normal")
    boss_shoot()

def boss_shoot():
    if not boss_active or boss is None or paused: return
    for dx in (-55,0,55):
        item=canvas.create_oval(boss["x"]+dx-6,boss["y"]+40,
                                boss["x"]+dx+6,boss["y"]+52,
                                fill="#fb7185",outline="#fff1f2")
        enemy_bullets.append({"item":item,"x":boss["x"]+dx,
                              "y":boss["y"]+47,"vx":dx*.025,
                              "vy":5.5+level*.15})
    root.after(max(400,900-level*20),boss_shoot)

def defeat_boss():
    global boss_active,boss,score
    burst(boss["x"],boss["y"],"#c084fc",90)
    score += 1000
    canvas.delete(boss["body"]); canvas.delete(boss["eye"])
    boss=None; boss_active=False
    canvas.itemconfig(boss_bg,state="hidden")
    canvas.itemconfig(boss_bar,state="hidden")

def activate_powerup(kind):
    global lives,invincible_timer
    if kind=="life": lives=min(MAX_LIVES,lives+1)
    elif kind=="rapid":
        global shoot_cooldown
        shoot_cooldown=0
    else: invincible_timer=300
    hud_update()

def game_loop():
    global player_x,score,level,spawn_timer,shoot_cooldown,invincible_timer,boss_hp

    if screen=="game" and not paused:
        if "left" in keys or "a" in keys: player_x -= PLAYER_SPEED
        if "right" in keys or "d" in keys: player_x += PLAYER_SPEED
        player_x=max(40,min(WIDTH-40,player_x))
        if "space" in keys: shoot()
        if shoot_cooldown: shoot_cooldown-=1
        draw_player()

        spawn_timer-=1
        if spawn_timer<=0 and not boss_active:
            spawn_asteroid()
            spawn_timer=max(14,48-level*2)

        new_level=score//500+1
        if new_level>level:
            level=new_level
            burst(WIDTH//2,HEIGHT//2,"#67e8f9",45)
            if level%5==0 and not boss_active: start_boss()

        for a in asteroids[:]:
            a["y"]+=a["speed"]; canvas.move(a["item"],0,a["speed"])
            if a["y"]-a["size"]>HEIGHT:
                canvas.delete(a["item"]); asteroids.remove(a); score+=5; continue
            if distance(a["x"],a["y"],player_x,player_y)<a["size"]+25:
                canvas.delete(a["item"]); asteroids.remove(a)
                burst(a["x"],a["y"],"#fb923c",22); hit_player()

        for b in bullets[:]:
            b["y"]-=b["speed"]; canvas.move(b["item"],0,-b["speed"])
            if b["y"]<-20:
                canvas.delete(b["item"]); bullets.remove(b); continue
            hit=False
            for a in asteroids[:]:
                if distance(b["x"],b["y"],a["x"],a["y"])<a["size"]+5:
                    a["hp"]-=1; burst(b["x"],b["y"],"#fde047",7)
                    canvas.delete(b["item"]); bullets.remove(b); hit=True
                    if a["hp"]<=0:
                        score+=25+a["size"]
                        burst(a["x"],a["y"],"#94a3b8",24)
                        if random.random()<.08: spawn_powerup(a["x"],a["y"])
                        canvas.delete(a["item"]); asteroids.remove(a)
                    break
            if not hit and boss_active and boss:
                if distance(b["x"],b["y"],boss["x"],boss["y"])<105:
                    boss_hp-=1; burst(b["x"],b["y"],"#c084fc",4)
                    canvas.delete(b["item"]); bullets.remove(b)
                    canvas.coords(boss_bar,250,52,250+400*max(0,boss_hp/boss_max_hp),66)
                    if boss_hp<=0: defeat_boss()

        for b in enemy_bullets[:]:
            b["x"]+=b["vx"]; b["y"]+=b["vy"]
            canvas.move(b["item"],b["vx"],b["vy"])
            if b["y"]>HEIGHT+20:
                canvas.delete(b["item"]); enemy_bullets.remove(b); continue
            if distance(b["x"],b["y"],player_x,player_y)<25:
                canvas.delete(b["item"]); enemy_bullets.remove(b); hit_player()

        if boss_active and boss:
            if boss["y"]<120:
                boss["y"]+=2; canvas.move(boss["body"],0,2); canvas.move(boss["eye"],0,2)
            else:
                boss["x"]+=boss["vx"]
                if boss["x"]<120 or boss["x"]>WIDTH-120: boss["vx"]*=-1
                canvas.move(boss["body"],boss["vx"],0)
                canvas.move(boss["eye"],boss["vx"],0)

        for p in powerups[:]:
            p["y"]+=2.2; canvas.move(p["item"],0,2.2); canvas.move(p["label"],0,2.2)
            if p["y"]>HEIGHT+20:
                canvas.delete(p["item"]);canvas.delete(p["label"]);powerups.remove(p);continue
            if distance(p["x"],p["y"],player_x,player_y)<32:
                activate_powerup(p["kind"]); burst(p["x"],p["y"],"#facc15",15)
                canvas.delete(p["item"]);canvas.delete(p["label"]);powerups.remove(p)

        if invincible_timer: invincible_timer-=1
        hud_update()

    update_particles()
    root.after(FPS,game_loop)

def clear_objects():
    for a in asteroids: canvas.delete(a["item"])
    for b in bullets: canvas.delete(b["item"])
    for b in enemy_bullets: canvas.delete(b["item"])
    for p in powerups:
        canvas.delete(p["item"]); canvas.delete(p["label"])
    for p in particles: canvas.delete(p[0])
    asteroids.clear(); bullets.clear(); enemy_bullets.clear()
    powerups.clear(); particles.clear()

def start_game():
    global screen,score,level,lives,paused,player_x,spawn_timer
    global boss,boss_active,boss_hp,boss_max_hp,shoot_cooldown,invincible_timer
    clear_objects()
    if boss:
        canvas.delete(boss["body"]);canvas.delete(boss["eye"])
    boss=None; boss_active=False
    canvas.itemconfig(boss_bg,state="hidden");canvas.itemconfig(boss_bar,state="hidden")
    score=0;level=1;lives=MAX_LIVES;paused=False
    player_x=WIDTH//2;spawn_timer=20;shoot_cooldown=0;invincible_timer=0
    screen="game"
    canvas.itemconfig(title,state="hidden");canvas.itemconfig(subtitle,state="hidden")
    canvas.itemconfig(menu,state="hidden");canvas.itemconfig(message,text="")
    draw_player();hud_update()

def show_menu():
    global screen,paused
    screen="menu";paused=False
    canvas.itemconfig(title,state="normal");canvas.itemconfig(subtitle,state="normal")
    canvas.itemconfig(menu,state="normal")
    canvas.itemconfig(menu,text=
        "DODGE  •  SHOOT  •  SURVIVE\n\n"
        "← → / A D     Move\n"
        "SPACE          Shoot\n"
        "P              Pause\n\n"
        "Press ENTER to Start\n\n"
        f"BEST SCORE: {high_score}")
    canvas.itemconfig(message,text="")

def pause_game():
    global paused
    if screen=="game":
        paused=not paused
        canvas.itemconfig(message,text="PAUSED\n\nPress P to continue" if paused else "")

def end_game():
    global screen,high_score
    screen="gameover"
    if score>high_score:
        high_score=score
        try: HIGH_SCORE_FILE.write_text(json.dumps({"high_score":high_score}))
        except Exception: pass
    canvas.itemconfig(message,text=
        f"GAME OVER\n\nSCORE: {score}\nLEVEL: {level}\nBEST: {high_score}\n\n"
        "Press ENTER to play again\nPress ESC for menu")

def key_down(event):
    key=event.keysym.lower();keys.add(key)
    if key=="return" and screen in ("menu","gameover"): start_game()
    elif key=="p": pause_game()
    elif key=="escape" and screen=="game": show_menu()

def key_up(event):
    keys.discard(event.keysym.lower())

def animate_stars():
    for item,speed,size in stars:
        canvas.move(item,0,speed)
        c=canvas.coords(item)
        if c and c[1]>HEIGHT:
            x=random.randrange(WIDTH);canvas.coords(item,x,0,x+size,size)
    root.after(35,animate_stars)

root.bind("<KeyPress>",key_down)
root.bind("<KeyRelease>",key_up)

show_menu()
animate_stars()
game_loop()
root.mainloop()
