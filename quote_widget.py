import os
import random
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QFont, QPainter, QPainterPath, QColor, QLinearGradient


class QuoteWidget(QWidget):
    """
    Minimal Quote Widget with glassmorphism effect
    Shows short inspirational quotes (wraps to 2nd line if needed)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Widget properties - compact and minimal
        self.setFixedWidth(200)  # allow height to expand
        self.setStyleSheet("background: transparent;")

        # Setup fonts
        self.setup_fonts()

        # Quote data
        self.quotes = [
            "Be yourself, everyone else is taken.",
            "Progress, not perfection.",
            "Small steps, big dreams.",
            "Today is your opportunity.",
            "Believe in your journey.",
            "Create your own sunshine.",
            "Choose joy every day.",
            "Make it happen.",
            "Stay curious, stay humble.",
            "Dream big, start small.",
            "Focus on the good.",
            "You are enough.",
            "Embrace the journey.",
            "Find your purpose.",
            "Stay positive, work hard."
        ]

        # Setup UI
        self.setup_ui()

        # Change quote every 60 seconds
        self.quote_timer = QTimer()
        self.quote_timer.timeout.connect(self.update_quote)
        self.quote_timer.start(60000)

    def setup_fonts(self):
        """Setup fonts with fallbacks"""
        font_loaded = False

        font_path = os.path.join(os.path.dirname(__file__), "fonts", "SF-Pro-Text-Thin.otf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                self.base_font = QFont(font_family)
                font_loaded = True

        if not font_loaded:
            fallback_fonts = ["SF Pro Text", "Segoe UI", "Helvetica Neue", "Arial"]
            for font_name in fallback_fonts:
                if font_name in QFontDatabase().families():
                    self.base_font = QFont(font_name)
                    font_loaded = True
                    break

        if not font_loaded:
            self.base_font = QFont("Arial")

    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(0)

        # Quote label - centered, can wrap
        self.quote_label = QLabel(random.choice(self.quotes))
        self.quote_label.setAlignment(Qt.AlignCenter)
        self.quote_label.setFont(QFont(self.base_font.family(), 12, QFont.Normal))
        self.quote_label.setStyleSheet("""
            color: white;
            font-weight: 400;
        """)
        self.quote_label.setWordWrap(True)   # enable wrapping

        layout.addWidget(self.quote_label)

    def update_quote(self):
        """Update to a new random quote"""
        new_quote = random.choice(self.quotes)
        while new_quote == self.quote_label.text() and len(self.quotes) > 1:
            new_quote = random.choice(self.quotes)
        self.quote_label.setText(new_quote)

    def paintEvent(self, event):
        """Custom paint event for glassmorphism background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 15, 15)

        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 30))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 20))
        gradient.setColorAt(1, QColor(255, 255, 255, 15))

        painter.fillPath(path, gradient)

        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawPath(path)

        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 14, 14)
        painter.setPen(QColor(255, 255, 255, 60))
        painter.drawPath(inner_path)
