from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.slider import Slider
from kivy.uix.dropdown import DropDown
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
import os

MUSIC_FOLDER = "music"
SPOTIFY_GREEN = (0.11, 0.73, 0.33, 1)
BACKGROUND = (0.07, 0.07, 0.07, 1)
PANEL_BG = (0.13, 0.13, 0.13, 1)
BUTTON_BG = (0.2, 0.2, 0.2, 1)
ALBUM_SIZE = 300

class BG(BoxLayout):
    def __init__(self, color, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update, pos=self._update)

    def _update(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

class PlayerUI(BG):
    def __init__(self, **kwargs):
        super().__init__(BACKGROUND, orientation="vertical", **kwargs)

        self.queue = []
        self.playlist = []
        self.index = 0
        self.sound = None

        self.ensure_music()

        # TOP BAR
        top = BG(BACKGROUND, size_hint_y=None, height=50)
        self.add_widget(top)

        playlists_btn = Button(text="Playlists", background_color=BUTTON_BG)
        playlists_btn.bind(on_release=self.open_playlists)
        top.add_widget(playlists_btn)

        queue_btn = Button(text="Queue", background_color=BUTTON_BG)
        queue_btn.bind(on_release=self.open_queue)
        top.add_widget(queue_btn)

        # ALBUM ART
        self.cover = Image(size_hint_y=None, height=ALBUM_SIZE)
        self.add_widget(self.cover)

        self.now_playing = Label(text="Now Playing: None", size_hint_y=None, height=40)
        self.add_widget(self.now_playing)

        self.time_label = Label(text="0:00 / 0:00", size_hint_y=None, height=30)
        self.add_widget(self.time_label)

        # BOTTOM CONTROLS
        bottom = BG(PANEL_BG, size_hint_y=None, height=160)
        self.add_widget(bottom)

        controls = BoxLayout(size_hint_y=None, height=60)
        bottom.add_widget(controls)

        controls.add_widget(Button(text="⏮", on_press=self.prev))
        controls.add_widget(Button(text="▶", on_press=self.play))
        controls.add_widget(Button(text="⏭", on_press=self.next))
        controls.add_widget(Button(text="🔀"))
        controls.add_widget(Button(text="🔁"))

        self.volume = Slider(min=0, max=1, value=0.7)
        self.volume.bind(value=self.set_volume)
        bottom.add_widget(self.volume)

        self.progress = Slider(min=0, max=1, value=0)
        self.progress.bind(on_touch_up=self.seek)
        bottom.add_widget(self.progress)

        Clock.schedule_interval(self.update_progress, 0.2)

    # ---------------- CORE ---------------- #

    def ensure_music(self):
        if not os.path.exists(MUSIC_FOLDER):
            os.makedirs(MUSIC_FOLDER)
        for f in os.listdir(MUSIC_FOLDER):
            if f.endswith((".mp3", ".wav", ".ogg")):
                self.playlist.append(os.path.join(MUSIC_FOLDER, f))

    def play(self, *args):
        if not self.playlist:
            return
        if self.sound:
            self.sound.stop()

        path = self.playlist[self.index]
        self.sound = SoundLoader.load(path)
        if self.sound:
            self.sound.volume = self.volume.value
            self.sound.play()
            self.now_playing.text = f"Now Playing: {os.path.basename(path)}"

    def next(self, *args):
        self.index = (self.index + 1) % len(self.playlist)
        self.play()

    def prev(self, *args):
        self.index = max(0, self.index - 1)
        self.play()

    def set_volume(self, instance, value):
        if self.sound:
            self.sound.volume = value

    def update_progress(self, dt):
        if self.sound and self.sound.length:
            self.progress.value = self.sound.get_pos() / self.sound.length

    def seek(self, instance, touch):
        if self.sound and instance.collide_point(*touch.pos):
            self.sound.stop()
            self.sound.play()
            self.sound.seek(instance.value * self.sound.length)

    # ---------------- DROPDOWNS ---------------- #

    def open_playlists(self, btn):
        dd = DropDown()
        for song in self.playlist:
            b = Button(text=os.path.basename(song), size_hint_y=None, height=44)
            b.bind(on_release=lambda x, p=song: self.select_song(p, dd))
            dd.add_widget(b)
        dd.open(btn)

    def open_queue(self, btn):
        dd = DropDown()
        for song in self.queue:
            dd.add_widget(Button(text=os.path.basename(song), size_hint_y=None, height=44))
        dd.open(btn)

    def select_song(self, path, dd):
        dd.dismiss()
        self.index = self.playlist.index(path)
        self.play()

class MusicApp(App):
    def build(self):
        return PlayerUI()

MusicApp().run()
