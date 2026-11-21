import time
import os
import json
import random
import re
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QFrame, QGraphicsOpacityEffect,
    QSizePolicy, QTextEdit, QProgressBar
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    Slot, QThread, Signal, QSize
)
from PySide6.QtGui import (
    QFontDatabase, QFont, QPainter, QPainterPath, QColor,
    QLinearGradient, QFontMetrics, QIcon, QPixmap, QTextCursor
)

try:
    import google.generativeai as genai

    HAVE_GENAI = True
except ImportError:
    HAVE_GENAI = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "icons")


def icon_or_empty(filename: str) -> QIcon:
    path = os.path.join(ASSETS_DIR, filename)
    return QIcon(path) if os.path.exists(path) else QIcon()


class GeminiWorkerThread(QThread):
    """Background thread for Gemini API calls"""
    response_ready = Signal(str, bool)  # response, is_error

    def __init__(self, api_key: str, query: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.query = query

    def run(self):
        try:
            if not HAVE_GENAI:
                self.response_ready.emit("❌ Google Generative AI library not installed", True)
                return

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            # Enhanced prompt for better responses
            enhanced_query = f"""Please provide a concise, helpful response to: {self.query}

Keep the response under 200 words and make it practical and actionable when possible."""

            response = model.generate_content(enhanced_query)

            if response and response.text:
                self.response_ready.emit(response.text.strip(), False)
            else:
                self.response_ready.emit("❌ No response received from Gemini", True)

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.response_ready.emit(error_msg, True)


class AnimatedResponseWidget(QFrame):
    """Widget to display responses with fade animations"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Response label
        self.response_label = QLabel("")
        self.response_label.setWordWrap(True)
        self.response_label.setTextFormat(Qt.RichText)
        self.response_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.response_label.setStyleSheet("""
            QLabel {
                color: #f0f0f0;
                font-size: 9px;
                font-weight: 400;
                line-height: 1.4;
                padding: 8px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        layout.addWidget(self.response_label)

        # Animation setup
        self.opacity_effect = QGraphicsOpacityEffect()
        self.response_label.setGraphicsEffect(self.opacity_effect)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(500)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

    def set_response(self, text: str, is_error: bool = False):
        """Set response text with fade animation"""
        color = "#ffcdd2" if is_error else "#f0f0f0"
        formatted_text = self._format_response(text)

        self.response_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 9px;
                font-weight: 400;
                line-height: 1.4;
                padding: 8px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)

        # Safe disconnect (prevents RuntimeWarning)
        try:
            self.fade_anim.finished.disconnect()
        except (TypeError, RuntimeError):
            pass

        # Fade out, then fade in new text
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(lambda: self._fade_in_new_text(formatted_text))
        self.fade_anim.start()

    def _fade_in_new_text(self, text: str):
        """Helper to fade in new text"""
        self.response_label.setText(text)

        try:
            self.fade_anim.finished.disconnect()
        except (TypeError, RuntimeError):
            pass

        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

    def _format_response(self, text: str) -> str:
        """Format response text with basic markdown-like styling"""
        # Convert **bold** to HTML
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Convert *italic* to HTML
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Add line breaks
        return text.replace('\n', '<br>')



class GeminiWidget(QWidget):
    """Enhanced Gemini AI widget with glassmorphism styling and animations"""

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)

        self.api_key = api_key
        self.worker_thread: Optional[GeminiWorkerThread] = None
        self.query_history: List[str] = []
        self.response_history: List[Dict[str, Any]] = []
        self.current_history_index = -1

        # Styling
        self.setStyleSheet("background: transparent;")
        self.setup_fonts()

        # Suggested queries that rotate
        self.suggested_queries = [
            "What's the weather like today?",
            "Give me a quick productivity tip",
            "What's a healthy breakfast idea?",
            "Tell me an interesting fact",
            "How can I improve my morning routine?",
            "What's a good 5-minute exercise?",
            "Suggest a motivational quote",
            "Quick skincare tip for today",
        ]

        self.setup_ui()
        self.setup_animations()

        # Auto-suggestion timer
        self.suggestion_timer = QTimer(self)
        self.suggestion_timer.timeout.connect(self._cycle_suggestion)
        self.suggestion_timer.start(4000)  # Change suggestion every 4 seconds
        self._cycle_suggestion()  # Start immediately

    def send_prompt(self, text: str):
        print(f"🎤 Gemini received voice text: {text}")
        self.submit_voice_query(text)  # <-- replace with the correct method you already have

    def setup_fonts(self):
        """Load custom fonts"""
        font_loaded = False
        font_path = os.path.join(BASE_DIR, "fonts", "SF-Pro-Text-Thin.otf")

        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    self.base_font = QFont(families[0])
                    font_loaded = True

        if not font_loaded:
            self.base_font = QFont("SF Pro Text", 9)

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Header with title and status
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title_label = QLabel("✨ AI Assistant")
        self.title_label.setFont(QFont(self.base_font.family(), 10, QFont.Weight.DemiBold))
        self.title_label.setStyleSheet("color: white;")

        self.status_label = QLabel("●")
        self.status_label.setFont(QFont(self.base_font.family(), 12))
        self.status_label.setStyleSheet("color: #4CAF50;")  # Green dot for ready
        self.status_label.setFixedWidth(20)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)

        # Input section
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask me anything...")
        self.query_input.setFont(QFont(self.base_font.family(), 9))
        self.query_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 9px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background: rgba(255, 255, 255, 0.15);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        self.query_input.returnPressed.connect(self._submit_query)

        # Buttons
        self.send_btn = QPushButton()
        self.send_btn.setIcon(icon_or_empty("send.svg"))
        self.send_btn.setIconSize(QSize(16, 16))
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76, 175, 80, 0.8);
                border: 1px solid rgba(76, 175, 80, 0.6);
                border-radius: 16px;
            }
            QPushButton:hover {
                background: rgba(76, 175, 80, 1.0);
            }
            QPushButton:pressed {
                background: rgba(56, 142, 60, 1.0);
            }
        """)
        self.send_btn.clicked.connect(self._submit_query)

        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(icon_or_empty("clear.svg"))
        self.clear_btn.setIconSize(QSize(14, 14))
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        self.clear_btn.clicked.connect(self._clear_response)

        input_layout.addWidget(self.query_input, 1)
        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.clear_btn)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                height: 6px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #81C784);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.hide()

        # Response area
        self.response_widget = AnimatedResponseWidget()

        # Quick actions
        quick_actions_layout = QHBoxLayout()
        quick_actions_layout.setSpacing(6)

        self.quick_tip_btn = QPushButton("💡 Tip")
        self.quick_fact_btn = QPushButton("🧠 Fact")
        self.quick_recipe_btn = QPushButton("🍳 Recipe")

        for btn in [self.quick_tip_btn, self.quick_fact_btn, self.quick_recipe_btn]:
            btn.setFont(QFont(self.base_font.family(), 8))
            btn.setFixedHeight(24)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 12px;
                    color: rgba(255, 255, 255, 0.8);
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.15);
                    color: white;
                }
            """)

        self.quick_tip_btn.clicked.connect(lambda: self._quick_query("Give me a quick productivity tip"))
        self.quick_fact_btn.clicked.connect(lambda: self._quick_query("Tell me an interesting fact"))
        self.quick_recipe_btn.clicked.connect(lambda: self._quick_query("Suggest a simple healthy recipe"))

        quick_actions_layout.addWidget(self.quick_tip_btn)
        quick_actions_layout.addWidget(self.quick_fact_btn)
        quick_actions_layout.addWidget(self.quick_recipe_btn)
        quick_actions_layout.addStretch()

        # Suggestion label
        self.suggestion_label = QLabel("")
        self.suggestion_label.setFont(QFont(self.base_font.family(), 8))
        self.suggestion_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-style: italic;")
        self.suggestion_label.setWordWrap(True)

        # Assembly
        main_layout.addLayout(header_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.response_widget, 1)
        main_layout.addLayout(quick_actions_layout)
        main_layout.addWidget(self.suggestion_label)

        # Size policy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def setup_animations(self):
        """Setup various animations"""
        self.status_pulse_timer = QTimer(self)
        self.status_pulse_timer.timeout.connect(self._pulse_status)

    def _cycle_suggestion(self):
        """Cycle through suggested queries"""
        if self.suggested_queries:
            suggestion = random.choice(self.suggested_queries)
            self.suggestion_label.setText(f"💭 Try: \"{suggestion}\"")

    def _pulse_status(self):
        """Pulse the status indicator during processing"""
        current_color = self.status_label.styleSheet()
        if "#4CAF50" in current_color:  # Green
            self.status_label.setStyleSheet("color: #FFC107;")  # Yellow
        else:
            self.status_label.setStyleSheet("color: #4CAF50;")  # Green

    def _submit_query(self):
        """Submit query to Gemini API"""
        query = self.query_input.text().strip()
        if not query:
            return

        self._execute_query(query)

    def _quick_query(self, query: str):
        """Execute a quick query"""
        self.query_input.setText(query)
        self._execute_query(query)

    def _execute_query(self, query: str):
        """Execute the actual query"""
        if self.worker_thread and self.worker_thread.isRunning():
            return

        # Update UI state
        self.query_input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.progress_bar.show()
        self.status_pulse_timer.start(500)
        self.status_label.setStyleSheet("color: #FFC107;")  # Yellow for processing

        # Add to history
        self.query_history.append(query)

        # Start worker thread
        self.worker_thread = GeminiWorkerThread(self.api_key, query)
        self.worker_thread.response_ready.connect(self._handle_response)
        self.worker_thread.finished.connect(self._reset_ui_state)
        self.worker_thread.start()

    def submit_voice_query(self, text: str):
        """Accepts voice-recognized text and runs it as query"""
        if text.strip():
            self.query_input.setText(text)
            self._execute_query(text)

    def _handle_response(self, response: str, is_error: bool):
        """Handle response from Gemini API"""
        # Store in history
        self.response_history.append({
            'query': self.query_input.text(),
            'response': response,
            'is_error': is_error,
            'timestamp': time.time()
        })

        # Update response widget
        self.response_widget.set_response(response, is_error)

        # Clear input if successful
        if not is_error:
            self.query_input.clear()

    def _reset_ui_state(self):
        """Reset UI to ready state"""
        self.query_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_pulse_timer.stop()
        self.status_label.setStyleSheet("color: #4CAF50;")  # Green for ready

    def _clear_response(self):
        """Clear the current response"""
        self.response_widget.set_response("", False)
        self.query_input.clear()
        self.query_input.setFocus()

    def paintEvent(self, event):
        """Custom paint event for glassmorphism effect"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)

        # Gradient background
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 35))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 25))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)

        # Border
        painter.setPen(QColor(255, 255, 255, 55))
        painter.drawPath(path)

        # Inner highlight
        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 17, 17)
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawPath(inner_path)