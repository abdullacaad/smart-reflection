import sys
import os
from dotenv import load_dotenv

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QSizePolicy, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFont, QIcon

# Widgets
from makeup_widget import MakeupSuggestionsWidget
from face_analysis_thread import EnhancedFaceAnalysisThread
from voice_controller import VoiceController
from weather import WeatherWidget
from news_widget import NewsWidget
from spotify_widget import SpotifyWidget
from gemini_widget import GeminiWidget
from time_widget import TimeWidget
from custom_calendar import ModernCalendar
from stocks_widget import StocksWidget
from music_widget import MusicWidget
from quote_widget import QuoteWidget

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and add your API keys."
        )
    return value


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Reflection")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(BASE_DIR, "icons", "app_icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        self.setGeometry(100, 100, 1200, 800)

        # ---------- SCROLL AREA ----------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Sleek Modern Scrollbar Style
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.35);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.6);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        # ---------- SCROLL CONTENT WIDGET ----------
        central_widget = QWidget()
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet("""
            #centralWidget {
                background-image: url(assets/background.svg);
                background-repeat: no-repeat;
                background-position: top center;
                background-size: cover;
            }
        """)

        # ---------- MAIN LAYOUT ----------
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 30)

        # ---------- INITIALIZE ALL WIDGETS ----------
        self._create_widgets()

        # ---------- FLEXIBLE GRID LAYOUT ----------
        self._setup_flexible_layout(main_layout)

    def _create_widgets(self):
        # Time Widget
        self.time = TimeWidget()
        self.time.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Calendar Widget
        self.calendar = ModernCalendar()
        self.calendar.setFixedWidth(200)
        self.calendar.setMinimumHeight(200)
        self.calendar.setMaximumHeight(220)
        self.calendar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Music Widget
        music_folder = os.path.join(os.path.dirname(__file__), "music_playlist")
        self.music = MusicWidget(music_folder=music_folder)
        self.music.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.music.setMaximumHeight(85)
        self.music.setMinimumHeight(85)
        self.music.setMinimumWidth(350)

        # Makeup Suggestions Widget
        self.makeup = MakeupSuggestionsWidget()
        self.makeup.setFixedWidth(350)
        self.makeup.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Gemini Widget (beneath makeup, same width)
        self.gemini = GeminiWidget(require_env("GEMINI_API_KEY"))
        self.gemini.setFixedWidth(350)
        self.gemini.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # Voice Controller - now with required parameters (using existing music widget)
        self.voice_controller = VoiceController(self.music, self.gemini)

        # ✅ Connect the signal to Gemini safely
        self.voice_controller.text_recognized.connect(self.gemini.send_prompt)
        self.voice_controller.start_listening()
        # Face analysis thread
        self.face_thread = EnhancedFaceAnalysisThread(camera_index=0, show_debug=True)
        self.face_thread.suggestion_ready.connect(self.makeup.set_suggestion_from_payload)
        self.face_thread.start()

        # Weather Widget
        self.weather = WeatherWidget(require_env("OPENWEATHER_API_KEY"))
        self.weather.setFixedSize(230, 150)
        self.weather.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Stocks Widget
        self.stocks = StocksWidget(
            api_key=require_env("ALPHA_VANTAGE_API_KEY"),
            base_url="https://www.alphavantage.co/query",
            symbol="AAPL"
        )
        self.stocks.setFixedWidth(200)
        self.stocks.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Quote Widget
        self.quote = QuoteWidget()
        self.quote.setFixedWidth(200)
        self.quote.setFixedHeight(70)
        self.quote.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # News Widget
        self.news = NewsWidget(require_env("NEWS_API_KEY"), country="us")
        self.news.setFixedWidth(200)
        self.news.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def _setup_flexible_layout(self, main_layout):
        """Grid layout system"""
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(30, 0, 30, 0)

        # Left column
        left_column_layout = QVBoxLayout()
        left_column_layout.setSpacing(12)
        left_column_layout.addWidget(self.time, 0, Qt.AlignTop | Qt.AlignLeft)
        left_column_layout.addWidget(self.calendar, 0, Qt.AlignTop | Qt.AlignLeft)
        left_column_layout.addWidget(self.music, 0, Qt.AlignTop | Qt.AlignLeft)
        left_column_layout.addWidget(self.makeup, 0, Qt.AlignTop | Qt.AlignLeft)
        left_column_layout.addWidget(self.gemini, 0, Qt.AlignTop | Qt.AlignLeft)
        left_column_layout.addStretch()

        left_column_widget = QWidget()
        left_column_widget.setLayout(left_column_layout)

        # Right column
        right_column_layout = QVBoxLayout()
        right_column_layout.setSpacing(8)
        self.weather.setFixedHeight(140)
        self.stocks.setFixedHeight(150)
        self.quote.setFixedHeight(70)
        right_column_layout.addWidget(self.weather, 0, Qt.AlignTop | Qt.AlignRight)
        right_column_layout.addWidget(self.stocks, 0, Qt.AlignTop | Qt.AlignRight)
        right_column_layout.addWidget(self.quote, 0, Qt.AlignTop | Qt.AlignRight)
        right_column_layout.addWidget(self.news, 1, Qt.AlignTop | Qt.AlignRight)

        right_column_widget = QWidget()
        right_column_widget.setLayout(right_column_layout)

        # Placement
        content_layout.addWidget(left_column_widget, 0, 0)
        content_layout.addWidget(right_column_widget, 0, 2)
        content_layout.setColumnStretch(0, 2)
        content_layout.setColumnStretch(1, 3)
        content_layout.setColumnStretch(2, 2)
        main_layout.addWidget(content_widget, 8)

    def closeEvent(self, event):
        try:
            if hasattr(self, "face_thread") and self.face_thread.isRunning():
                self.face_thread.stop()
                self.face_thread.wait(1500)
        except Exception:
            pass
        super().closeEvent(event)


def load_fonts():
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    if os.path.exists(font_dir):
        for filename in os.listdir(font_dir):
            if filename.lower().endswith((".otf", ".ttf")):
                QFontDatabase.addApplicationFont(os.path.join(font_dir, filename))


def main():
    app = QApplication(sys.argv)
    load_fonts()
    try:
        families = QFontDatabase.applicationFontFamilies(
            QFontDatabase.addApplicationFont("fonts/SF-Pro-Text-Thin.otf")
        )
        if families:
            app.setFont(QFont(families[0], 13))
    except Exception:
        app.setFont(QFont("Arial", 13))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
