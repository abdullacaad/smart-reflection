# music_widget.py
import os
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import (
    QPixmap, QIcon, QFontMetrics, QFontDatabase, QFont,
    QPainter, QPainterPath, QColor, QLinearGradient
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

try:
    from mutagen.id3 import ID3
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4

    HAVE_MUTAGEN = True
except Exception:
    HAVE_MUTAGEN = False

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")
MUSIC_DIR_DEFAULT = "music_playlist"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "icons")


def icon_or_empty(filename: str) -> QIcon:
    path = os.path.join(ASSETS_DIR, filename)
    return QIcon(path) if os.path.exists(path) else QIcon()


class MusicWidget(QFrame):
    def __init__(self, music_folder: str | None = None, parent=None):
        super().__init__(parent)

        # --- Styling (remove solid bg, keep rounded) ---
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border-radius: 12px;
            }
            QLabel { 
                color: #eaeaea; 
            }
            QSlider::groove:horizontal {
                height: 2px;
                background: rgba(255, 255, 255, 0.25);
                border-radius: 1px;
                margin: 0px;
                border: none;
            }
            QSlider::sub-page:horizontal { 
                background: rgba(255, 255, 255, 0.8); 
                border-radius: 1px;
                border: none;
            }
            QSlider::add-page:horizontal {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 1px;
                border: none;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                width: 8px;
                height: 8px;
                margin: -3px 0;
                border-radius: 4px;
                border: none;
                box-shadow: none;
            }
            QSlider::handle:horizontal:hover {
                background: #ffffff;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:pressed {
                background: #ffffff;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QPushButton { 
                border: none; 
                background: transparent;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.2);
            }
        """)

        # --- Paths & tracks ---
        self.music_folder = music_folder or MUSIC_DIR_DEFAULT
        os.makedirs(self.music_folder, exist_ok=True)
        self.tracks = self._scan_folder(self.music_folder)
        self.index, self.user_scrubbing = 0, False

        # --- Player ---
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.7)

        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.playbackStateChanged.connect(self._on_playback_state)

        # --- UI Layout ---
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)  # Better padding
        root.setSpacing(12)  # Increased spacing

        # Cover - slightly smaller and more compact
        self.cover = QLabel()
        self.cover.setFixedSize(50, 50)  # Reduced from 60x60
        self.cover.setAlignment(Qt.AlignCenter)

        # Fonts
        fonts_dir = os.path.join(BASE_DIR, "fonts")
        if os.path.exists(fonts_dir):
            for fname in os.listdir(fonts_dir):
                if fname.lower().endswith((".ttf", ".otf")):
                    QFontDatabase.addApplicationFont(os.path.join(fonts_dir, fname))
        self.setFont(QFont("SF-Mono-Regular", 9))  # Slightly smaller font

        # Center column (title, artist, slider)
        center_col = QVBoxLayout()
        center_col.setSpacing(2)  # Tighter spacing
        center_col.setContentsMargins(0, 2, 0, 2)

        # Title with wider width and better sizing
        self.title = QLabel("No Song")
        self.title.setStyleSheet("font-weight: 600; color: #f5f5f5; font-size: 12px;")
        self.title.setWordWrap(False)
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.title.setMinimumWidth(250)  # Increased from 180
        self.title.setMaximumHeight(16)

        # Artist label
        self.artist = QLabel("Unknown Artist")
        self.artist.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.65);")
        self.artist.setWordWrap(False)  # Changed to False for single line
        self.artist.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.artist.setMaximumHeight(14)

        # Progress slider with better positioning - reduced height for sleeker look
        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setFixedHeight(16)  # Reduced from 20 for thinner appearance
        self.progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress.sliderPressed.connect(self._on_slider_pressed)
        self.progress.sliderReleased.connect(self._on_slider_released)
        self.progress.sliderMoved.connect(self._on_slider_moved)

        center_col.addWidget(self.title)
        center_col.addWidget(self.artist)
        center_col.addSpacing(4)  # Add small space before slider
        center_col.addWidget(self.progress)

        # Controls with smaller buttons
        controls = QHBoxLayout()
        controls.setSpacing(4)  # Tighter spacing
        controls.setContentsMargins(0, 0, 0, 0)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(icon_or_empty("prev.svg"))
        self.btn_prev.setIconSize(QSize(16, 16))  # Reduced from 20x20
        self.btn_prev.setFixedSize(24, 24)  # Reduced from 28x28
        self.btn_prev.clicked.connect(self.prev_track)

        self.btn_play = QPushButton()
        self.btn_play.setIcon(icon_or_empty("play.svg"))
        self.btn_play.setIconSize(QSize(18, 18))  # Reduced from 24x24
        self.btn_play.setFixedSize(28, 28)  # Reduced from 32x32
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(icon_or_empty("next.svg"))
        self.btn_next.setIconSize(QSize(16, 16))  # Reduced from 20x20
        self.btn_next.setFixedSize(24, 24)  # Reduced from 28x28
        self.btn_next.clicked.connect(self.next_track)

        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_next)
        controls.addStretch()  # Push buttons to the left

        # Assemble with better proportions
        root.addWidget(self.cover, 0, Qt.AlignVCenter)
        root.addLayout(center_col, 1)
        root.addLayout(controls, 0)

        # Better stretch factors for more balanced layout
        root.setStretch(0, 0)  # Cover: fixed
        root.setStretch(1, 4)  # Center: more space for wider text
        root.setStretch(2, 1)  # Controls: compact

        # --- Init with more compact size ---
        self.setMaximumHeight(85)  # Reduced from 120
        self.setMinimumHeight(85)
        self.setMinimumWidth(350)  # Ensure minimum width for text

        if not self.tracks:
            self._set_disabled(True)
            self._set_cover_fallback()
            self.title.setText(f'No audio files in "{self.music_folder}"')
        else:
            self._load_current(play=True)

    # === Helpers ===
    def _scan_folder(self, folder: str):
        try:
            return [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(AUDIO_EXTS)]
        except Exception:
            return []

    def _set_disabled(self, disabled: bool):
        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.setDisabled(disabled)
        self.progress.setDisabled(disabled)

    def _rounded_pixmap(self, pix: QPixmap, size: QSize, radius: int = 6) -> QPixmap:
        """Return a scaled pixmap clipped into rounded rect"""
        if pix.isNull():
            return pix
        scaled = pix.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        result = QPixmap(size)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
        painter.setClipPath(path)
        x = (size.width() - scaled.width()) // 2
        y = (size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
        return result

    def _set_cover_fallback(self):
        fallback = os.path.join(ASSETS_DIR, "default_cover.png")
        if os.path.exists(fallback):
            pix = QPixmap(fallback)
            rounded = self._rounded_pixmap(pix, self.cover.size(), radius=6)
            self.cover.setPixmap(rounded)
        else:
            self.cover.setText("🎵")

    def _elide(self, label: QLabel, text: str):
        fm = QFontMetrics(label.font())
        # Increased available width for text
        available_width = 240  # Increased from 140
        elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, available_width)
        label.setText(elided)

    def _read_tags(self, path: str):
        title, artist = os.path.basename(path), ""
        if not HAVE_MUTAGEN:
            return title, artist
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".mp3":
                audio = MP3(path, ID3=ID3)
                t, a = audio.get("TIT2"), audio.get("TPE1")
                if t and t.text: title = t.text[0]
                if a and a.text: artist = a.text[0]
            elif ext in (".m4a", ".aac"):
                mp4 = MP4(path)
                if "©nam" in mp4: title = mp4["©nam"][0]
                if "©ART" in mp4: artist = mp4["©ART"][0]
        except Exception:
            pass
        return title, artist

    def _read_cover(self, path: str):
        if not HAVE_MUTAGEN:
            return None
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".mp3":
                audio = MP3(path, ID3=ID3)
                if audio.tags:
                    for frame in audio.tags.values():
                        if getattr(frame, "FrameID", "") == "APIC" and getattr(frame, "data", None):
                            pix = QPixmap();
                            pix.loadFromData(frame.data);
                            return pix
            elif ext in (".m4a", ".aac"):
                mp4 = MP4(path);
                covr = mp4.tags.get("covr")
                if covr:
                    data = covr[0];
                    pix = QPixmap();
                    pix.loadFromData(bytes(data));
                    return pix
        except Exception:
            pass
        return None

    def _load_current(self, play: bool = False):
        path = self.tracks[self.index]
        self.player.setSource(QUrl.fromLocalFile(path))
        title, artist = self._read_tags(path)
        self._elide(self.title, title or os.path.basename(path))
        self._elide(self.artist, artist or "Unknown Artist")
        cover = self._read_cover(path)
        if cover:
            rounded = self._rounded_pixmap(cover, self.cover.size(), radius=6)
            self.cover.setPixmap(rounded)
        else:
            self._set_cover_fallback()
        if play:
            self.player.play()

    # === Controls ===
    def toggle_play(self):
        self.player.pause() if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState else self.player.play()

    def next_track(self):
        if self.tracks:
            self.index = (self.index + 1) % len(self.tracks)
            self._load_current(play=True)

    def prev_track(self):
        if self.tracks:
            self.index = (self.index - 1) % len(self.tracks)
            self._load_current(play=True)

    # === Player signals ===
    def _on_position(self, pos):
        if not self.user_scrubbing:
            self.progress.setValue(pos)

    def _on_duration(self, dur):
        self.progress.setRange(0, max(0, dur))

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_track()

    def _on_playback_state(self, state):
        self.btn_play.setIcon(
            icon_or_empty("pause.svg") if state == QMediaPlayer.PlaybackState.PlayingState else icon_or_empty(
                "play.svg"))

    # === Glassmorphism Background ===
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)  # Tighter margins

        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)  # Slightly smaller radius

        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 40))  # Slightly more opaque
        gradient.setColorAt(0.5, QColor(255, 255, 255, 28))
        gradient.setColorAt(1, QColor(255, 255, 255, 22))
        painter.fillPath(path, gradient)

        painter.setPen(QColor(255, 255, 255, 55))
        painter.drawPath(path)

        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 11, 11)
        painter.setPen(QColor(255, 255, 255, 80))
        painter.drawPath(inner_path)

    # === Slider ===
    def _on_slider_pressed(self):
        self.user_scrubbing = True

    def _on_slider_released(self):
        self.user_scrubbing = False
        self.player.setPosition(self.progress.value())

    def _on_slider_moved(self, value):
        if self.user_scrubbing:
            self.player.setPosition(value)