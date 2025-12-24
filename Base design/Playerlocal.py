import os
import shutil
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk
import pygame
import random
import time
import numpy as np
import soundfile as sf

# ---------------------------- CONFIG -------------------------------- #
MUSIC_FOLDER = "music"
SPOTIFY_GREEN = "#1DB954"
BACKGROUND = "#111"
PANEL_BG = "#222"
BUTTON_BG = "#333"
BUTTON_FG = "white"
ALBUM_SIZE = 300  # px

pygame.mixer.init()

# ---------------------------- GLOBAL STATE --------------------------- #
playlist_dict = {}
playlist_paths = []
playlist_names = []
queue = []
queue_paths = []
invisible_queue_paths = []
invisible_queue_index = 0
current_index = 0
current_song_length = 0.0
current_position = 0.0
is_paused = False
is_seeking = False
seek_preview = 0.0
shuffle_mode = False
repeat_mode = "off"
album_image = None
song_start_time = 0.0
seeked_time = 0.0
history_paths = []
history_index = -1

# Visualizer & Game
visualizer_samples = np.array([])
visualizer_sample_rate = 44100
ripples = []

game_blocks = []
block_size = 40
score = 0
lives = 5
game_over = False
difficulty = "Medium"
block_speed_dict = {"Easy": 2, "Medium": 4, "Hard": 6}
spawn_interval_dict = {"Easy": 1500, "Medium": 1000, "Hard": 700}
last_spawn_time = 0
# ---------------------------- HELPERS -------------------------------- #
def format_time(seconds):
    try:
        s = int(seconds)
    except:
        s = 0
    return f"{s//60}:{s%60:02d}"

def find_album_art_for(song_path):
    folder = os.path.dirname(song_path)
    for candidate in ("cover.jpg", "folder.jpg", "cover.png", "folder.png"):
        p = os.path.join(folder, candidate)
        if os.path.exists(p):
            return p
    return None

def ensure_music_folder():
    if not os.path.exists(MUSIC_FOLDER):
        os.makedirs(MUSIC_FOLDER)

def scan_playlists():
    ensure_music_folder()
    result = {}
    for root, dirs, files in os.walk(MUSIC_FOLDER):
        rel = os.path.relpath(root, MUSIC_FOLDER)
        if rel == ".":
            continue
        audio_files = [f for f in files if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac"))]
        if audio_files:
            result[rel] = root
    return result

def load_playlist(path):
    names = []
    paths = []
    for root, dirs, files in os.walk(path):
        for f in sorted(files):
            if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac")):
                names.append(f)
                paths.append(os.path.join(root, f))
    return names, paths

def load_album_image(song_path):
    global album_image
    art_path = find_album_art_for(song_path)
    if art_path:
        try:
            img = Image.open(art_path).resize((ALBUM_SIZE, ALBUM_SIZE))
        except Exception:
            img = Image.new("RGB", (ALBUM_SIZE, ALBUM_SIZE), color="#444")
    else:
        img = Image.new("RGB", (ALBUM_SIZE, ALBUM_SIZE), color="#444")
    album_image = ImageTk.PhotoImage(img)
    album_label.config(image=album_image)

def random_color():
    r = random.randint(100, 255)
    g = random.randint(100, 255)
    b = random.randint(100, 255)
    return f'#{r:02x}{g:02x}{b:02x}'

# ---------------------------- PLAYER ACTIONS -------------------------- #
def play_song(path, playlist=None, index=None, use_invisible=True):
    global current_song_length, current_position, is_paused, song_start_time, seeked_time
    global invisible_queue_paths, invisible_queue_index, current_index, playlist_paths
    global history_paths, history_index, playlist_names
    global visualizer_samples, visualizer_sample_rate

    if not path:
        return

    current_position = 0.0
    seeked_time = 0.0
    song_start_time = time.time()

    if playlist is not None and index is not None and use_invisible:
        invisible_queue_paths = playlist
        invisible_queue_index = index
        playlist_paths = playlist
        current_index = index
        playlist_names, _ = load_playlist(os.path.dirname(playlist[index]))

    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(start=current_position)
    except Exception as e:
        print("Playback error:", e)
        return

    if history_index == -1 or (history_paths and path != history_paths[history_index]):
        history_paths = history_paths[:history_index+1]
        history_paths.append(path)
        history_index += 1

    is_paused = False

    try:
        snd = pygame.mixer.Sound(path)
        current_song_length = float(snd.get_length())
    except:
        current_song_length = 0.0

    now_playing_label.config(text=f"Now Playing: {os.path.basename(path)}")
    load_album_image(path)

    # Preload visualizer
    try:
        data, samplerate = sf.read(path, dtype='float32')
        if len(data.shape) > 1:
            data = data[:,0]
        visualizer_samples = data
        visualizer_sample_rate = samplerate
    except Exception as e:
        visualizer_samples = np.array([])
        visualizer_sample_rate = 44100
        print("Visualizer load error:", e)

def play_next_song():
    global invisible_queue_index
    if queue_paths:
        path = queue_paths.pop(0)
        queue.pop(0)
        refresh_queue_dropdown()
        play_song(path, use_invisible=False)
    elif invisible_queue_paths:
        invisible_queue_index += 1
        if invisible_queue_index >= len(invisible_queue_paths):
            if repeat_mode == "playlist":
                invisible_queue_index = 0
            else:
                return
        play_song(invisible_queue_paths[invisible_queue_index], use_invisible=False)

def play_prev_song():
    global history_index
    if history_index > 0:
        history_index -= 1
        play_song(history_paths[history_index], use_invisible=False)

def toggle_pause():
    global is_paused
    if is_paused:
        pygame.mixer.music.unpause()
        is_paused = False
        play_button.config(text="⏸")
    else:
        pygame.mixer.music.pause()
        is_paused = True
        play_button.config(text="▶")

def toggle_shuffle():
    global shuffle_mode
    shuffle_mode = not shuffle_mode
    shuffle_button.config(bg=SPOTIFY_GREEN if shuffle_mode else BUTTON_BG)

def toggle_repeat():
    global repeat_mode
    if repeat_mode == "off":
        repeat_mode = "playlist"
        repeat_button.config(bg=SPOTIFY_GREEN, text="🔁")
        repeat_label.config(text="")
    elif repeat_mode == "playlist":
        repeat_mode = "song"
        repeat_button.config(bg=SPOTIFY_GREEN, text="🔁")
        repeat_label.config(text="loop")
    else:
        repeat_mode = "off"
        repeat_button.config(bg=BUTTON_BG, text="🔁")
        repeat_label.config(text="")

# ---------------------------- SEEK & PROGRESS ------------------------ #
def start_seek(event):
    global is_seeking
    is_seeking = True
    seek_to(event)

def seek_to(event):
    global seek_preview
    if current_song_length > 0:
        widget = event.widget
        x = event.x
        width = widget.winfo_width()
        percent = max(0.0, min(1.0, x/width))
        seek_preview = percent * current_song_length
        time_label.config(text=f"{format_time(seek_preview)} / {format_time(current_song_length)}")
        progress_var.set(percent*100)

def stop_seek(event):
    global is_seeking, current_position, seeked_time, song_start_time
    is_seeking = False
    current_position = seek_preview
    seeked_time = current_position
    song_start_time = time.time()
    try:
        pygame.mixer.music.play(start=current_position)
        if is_paused:
            pygame.mixer.music.pause()
    except:
        pass

def update_progress():
    global current_position
    if pygame.mixer.music.get_busy() and not is_seeking:
        current_position = seeked_time + (time.time() - song_start_time)
    if current_song_length > 0:
        percent = min(current_position / current_song_length, 1.0)
        progress_var.set(percent*100)
        time_label.config(text=f"{format_time(current_position)} / {format_time(current_song_length)}")
        if current_position >= current_song_length - 0.1 and not is_paused:
            if repeat_mode == "song":
                play_song(history_paths[history_index], use_invisible=False)
            else:
                play_next_song()
    root.after(200, update_progress)

# ---------------------------- QUEUE & PLAYLIST ------------------------ #
def refresh_queue_dropdown():
    queue_mb.menu.delete(0, "end")
    if not queue:
        queue_mb.menu.add_command(label="(Queue empty)", state="disabled")
        return
    for i, song in enumerate(queue):
        song_menu = tk.Menu(queue_mb.menu, tearoff=False, bg=BUTTON_BG, fg="white")
        song_menu.add_command(label="▶ Play", command=lambda idx=i: play_song(queue_paths[idx], use_invisible=False))
        song_menu.add_command(label="❌ Remove from Queue", command=lambda idx=i: remove_from_queue(idx))
        queue_mb.menu.add_cascade(label=song, menu=song_menu)

def remove_from_queue(index):
    if 0 <= index < len(queue):
        queue.pop(index)
        queue_paths.pop(index)
        refresh_queue_dropdown()

def add_to_queue(name, path):
    queue.append(name)
    queue_paths.append(path)
    refresh_queue_dropdown()

def refresh_playlists_dropdown():
    master_playlist_mb.menu.delete(0, "end")
    for playlist_name, folder in playlist_dict.items():
        song_names, song_paths = load_playlist(folder)
        submenu = tk.Menu(master_playlist_mb.menu, tearoff=False, bg=BUTTON_BG, fg="white")
        for i, song_name in enumerate(song_names):
            song_submenu = tk.Menu(submenu, tearoff=False, bg=BUTTON_BG, fg="white")
            song_submenu.add_command(label="▶ Play", command=lambda p=song_paths[i], pl=song_paths, idx=i: play_song(p, pl, idx))
            song_submenu.add_command(label="+ Queue", command=lambda n=song_name, p=song_paths[i]: add_to_queue(n, p))
            submenu.add_cascade(label=song_name, menu=song_submenu)
        master_playlist_mb.menu.add_cascade(label=playlist_name, menu=submenu)
    master_playlist_mb.menu.add_separator()
    master_playlist_mb.menu.add_command(label="Add Folder", command=add_playlist_folder)

def add_playlist_folder():
    folder = filedialog.askdirectory(initialdir=MUSIC_FOLDER)
    if folder:
        dest = os.path.join(MUSIC_FOLDER, os.path.basename(folder))
        if not os.path.exists(dest):
            shutil.copytree(folder, dest)
        playlist_dict[os.path.basename(dest)] = dest
        refresh_playlists_dropdown()

# ---------------------------- GUI SETUP ------------------------------- #
root = tk.Tk()
root.title("Spotify Clone")
root.configure(bg=BACKGROUND)
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
root.geometry(f"{int(screen_w*0.7)}x{int(screen_h*0.7)}")

# Tabs
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

player_tab = tk.Frame(notebook, bg=BACKGROUND)
notebook.add(player_tab, text="Player")


# Top Frame
top_frame = tk.Frame(player_tab, bg=BACKGROUND)
top_frame.pack(fill="x", pady=4)

master_playlist_mb = tk.Menubutton(top_frame, text="Playlists", bg=BUTTON_BG, fg="white", relief="raised")
master_playlist_mb.pack(side="left", padx=4)
master_playlist_mb.menu = tk.Menu(master_playlist_mb, tearoff=False, bg=BUTTON_BG, fg="white")
master_playlist_mb["menu"] = master_playlist_mb.menu

queue_mb = tk.Menubutton(top_frame, text="Queue", bg=BUTTON_BG, fg="white", relief="raised")
queue_mb.pack(side="left", padx=4)
queue_mb.menu = tk.Menu(queue_mb, tearoff=False, bg=BUTTON_BG, fg="white")
queue_mb["menu"] = queue_mb.menu

ensure_music_folder()
playlist_dict = scan_playlists()
refresh_playlists_dropdown()

# Right Frame
right_frame = tk.Frame(player_tab, bg=BACKGROUND)
right_frame.pack(fill="both", expand=True)

album_label = tk.Label(right_frame, bg=BACKGROUND)
album_label.pack(pady=12)

now_playing_label = tk.Label(right_frame, text="Now Playing: None", fg="white", bg=BACKGROUND, font=("Arial",16))
now_playing_label.pack(pady=4)

time_label = tk.Label(right_frame, text="0:00 / 0:00", fg="white", bg=BACKGROUND, font=("Arial",12))
time_label.pack(pady=2)


# ----------------- BOTTOM CONTROLS ----------------- #
bottom = tk.Frame(right_frame, bg=PANEL_BG)
bottom.pack(side="bottom", fill="x", padx=8, pady=8)

def make_btn(master, txt, size=16, cmd=None):
    return tk.Button(master, text=txt, font=("Arial", size), width=4, bg=BUTTON_BG, fg=BUTTON_FG, relief="flat", command=cmd, activebackground=SPOTIFY_GREEN)

controls = tk.Frame(bottom, bg=PANEL_BG)
controls.pack()

prev_btn = make_btn(controls, "⏮", 18, play_prev_song)
prev_btn.grid(row=0, column=0, padx=6)
play_button = make_btn(controls, "⏸", 22, toggle_pause)
play_button.grid(row=0, column=1, padx=6)
next_btn = make_btn(controls, "⏭", 18, play_next_song)
next_btn.grid(row=0, column=2, padx=6)
shuffle_button = make_btn(controls, "🔀", 14, toggle_shuffle)
shuffle_button.grid(row=0, column=3, padx=6)
repeat_button = make_btn(controls, "🔁", 14, toggle_repeat)
repeat_button.grid(row=0, column=4, padx=6)
repeat_label = tk.Label(controls, text="", bg=PANEL_BG, fg=SPOTIFY_GREEN, font=("Arial",10))
repeat_label.grid(row=0, column=5, padx=6)

volume_var = tk.DoubleVar(value=0.3)
volume_slider = tk.Scale(controls, from_=0, to=1, resolution=0.01, orient="horizontal", variable=volume_var,
                         command=lambda v: pygame.mixer.music.set_volume(float(v)), length=140, bg=PANEL_BG, fg="white")
volume_slider.grid(row=0, column=6, padx=8)

# Progress bar
progress_var = tk.DoubleVar()
progress_bar = tk.Scale(bottom, variable=progress_var, from_=0, to=100, orient="horizontal", length=520,
                        showvalue=0, bg="white", troughcolor="#888")
progress_bar.pack(pady=8, padx=8, fill="x")
progress_bar.bind("<Button-1>", start_seek)
progress_bar.bind("<B1-Motion>", seek_to)
progress_bar.bind("<ButtonRelease-1>", stop_seek)

pygame.mixer.music.set_volume(volume_var.get())


# ----------------- INITIALIZE ----------------- #

update_progress()
root.mainloop()
