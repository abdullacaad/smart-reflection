# spotify_widget.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt


class SpotifyWidget(QFrame):
    def __init__(self, client_id, client_secret, redirect_uri):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #1DB954;
                border-radius: 15px;
                padding: 20px;
            }
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #121212;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton {
                background-color: #191414;
                color: white;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """)
        # Limit overall height of Spotify widget
        self.setMaximumHeight(220)  # adjust as needed
        layout = QVBoxLayout(self)

        self.label = QLabel(" Spotify Music")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(80)  # ensure buttons remain visible
        layout.addWidget(self.output)

        # Control buttons
        self.play_button = QPushButton("▶️ Play/Pause")
        self.next_button = QPushButton("⏭ Next")
        self.prev_button = QPushButton("⏮ Previous")
        layout.addWidget(self.play_button)
        layout.addWidget(self.next_button)
        layout.addWidget(self.prev_button)

        # Spotify Auth
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-read-playback-state,user-modify-playback-state,user-read-currently-playing,user-library-read"
        ))

        self.refresh_playing()

    def refresh_playing(self):
        try:
            track = self.sp.current_user_playing_track()
            if track and track['item']:
                name = track['item']['name']
                artist = track['item']['artists'][0]['name']
                self.output.setPlainText(f"Now Playing:\n{name} - {artist}")
            else:
                self.output.setPlainText("Nothing is playing right now.")
        except Exception as e:
            self.output.setPlainText(f"Error: {str(e)}")

    def toggle_playback(self):
        try:
            playback = self.sp.current_playback()
            if playback and playback['is_playing']:
                self.sp.pause_playback()
            else:
                self.sp.start_playback()
            self.refresh_playing()
        except Exception as e:
            self.output.setPlainText(f"Error: {str(e)}")

    def next_track(self):
        try:
            self.sp.next_track()
            self.refresh_playing()
        except Exception as e:
            self.output.setPlainText(f"Error: {str(e)}")

    def prev_track(self):
        try:
            self.sp.previous_track()
            self.refresh_playing()
        except Exception as e:
            self.output.setPlainText(f"Error: {str(e)}")
