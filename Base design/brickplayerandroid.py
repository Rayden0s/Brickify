# main.py
import os
import json
import webbrowser
from kivy.core.audio import SoundLoader
from kivy.properties import StringProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.list import OneLineListItem

# Path to save playlists
PLAYLIST_FILE = "playlists.json"

class MusicPlayer(BoxLayout):
    now_playing_text = StringProperty("No song playing")
    playlists = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sound = None
        self.load_playlists()

    def load_playlists(self):
        if os.path.exists(PLAYLIST_FILE):
            with open(PLAYLIST_FILE, "r") as f:
                self.playlists = json.load(f)
        else:
            self.playlists = []

        self.update_playlist_list()

    def save_playlists(self):
        with open(PLAYLIST_FILE, "w") as f:
            json.dump(self.playlists, f)

    def update_playlist_list(self):
        self.ids.playlist_list.clear_widgets()
        for folder in self.playlists:
            item = OneLineListItem(
                text=folder,
                on_release=lambda x, folder=folder: self.open_playlist(folder)
            )
            item.bind(on_touch_down=self.check_double_tap)
            self.ids.playlist_list.add_widget(item)

    def add_playlist(self):
        # Simple example: ask user to input folder path
        folder = input("Enter full folder path for playlist: ")
        if os.path.exists(folder) and folder not in self.playlists:
            self.playlists.append(folder)
            self.save_playlists()
            self.update_playlist_list()

    def open_playlist(self, folder):
        if os.path.exists(folder):
            webbrowser.open(folder)  # opens folder in file explorer
        else:
            print("Folder not found")

    def check_double_tap(self, instance, touch):
        if touch.is_double_tap:
            self.open_playlist(instance.text)

    def play_song(self, path):
        if self.sound:
            self.sound.stop()
        self.sound = SoundLoader.load(path)
        if self.sound:
            self.sound.play()
            self.now_playing_text = os.path.basename(path)

    def toggle_play(self):
        if self.sound:
            if self.sound.state == "play":
                self.sound.stop()
            else:
                self.sound.play()

KV = '''
<MusicPlayer>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    MDLabel:
        id: now_playing
        text: root.now_playing_text
        halign: 'center'
        theme_text_color: 'Custom'
        text_color: 1,1,1,1
        font_style: 'H6'

    ScrollView:
        MDList:
            id: playlist_list

    BoxLayout:
        size_hint_y: None
        height: "50dp"
        spacing: 10

        MDRaisedButton:
            text: "Add Playlist"
            on_release: root.add_playlist()

        MDRaisedButton:
            text: "Play/Pause"
            on_release: root.toggle_play()
'''

class MusicApp(MDApp):
    def build(self):
        from kivy.lang import Builder
        Builder.load_string(KV)
        return MusicPlayer()

if __name__ == "__main__":
    MusicApp().run()
