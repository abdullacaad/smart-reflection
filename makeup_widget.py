import os
import random
import re
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Slot
from PySide6.QtGui import QFontDatabase, QFont, QPainter, QPainterPath, QColor, QLinearGradient, QFontMetrics


class MakeupSuggestionsWidget(QWidget):
    """
    Grooming and Fashion Suggestions Widget with animations.
    Shows tips sequentially (one line at a time) with fade + flexible height.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumWidth(400)
        self.setStyleSheet("background: transparent;")
        self.setup_fonts()

        # Default fallback suggestions
        self.suggestions = [
            "✨ Light tinted moisturizer • Clear brow gel • Soft lip balm",
            "🌿 BB cream with SPF • Groomed eyebrows • Hydrating lip tint",
            "💫 Even skin tone • Defined brows • Natural lip moisture",
            "🌸 Gentle concealer • Brushed-up brows • Glossy lip balm",
            "👁️ Clean, natural look • Well-shaped brows • Smooth lips",
            "🌟 Dewy skin finish • Neat brow lines • Tinted lip care",
        ]

        # Animation state
        self._tips = []
        self._tip_index = 0
        self._cycle_running = False
        self._live_mode = False

        self.min_height = 80
        self.max_height = 220  # cap height

        self.setup_ui()
        self._setup_animations()

        # Start fallback after short delay
        self.fallback_timer = QTimer(self)
        self.fallback_timer.setSingleShot(True)
        self.fallback_timer.timeout.connect(self._start_fallback_cycle)
        self.fallback_timer.start(500)

    # ---------------- Fonts ----------------
    def setup_fonts(self):
        font_loaded = False
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "SF-Pro-Text-Thin.otf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                self.base_font = QFont(font_family)
                font_loaded = True

        if not font_loaded:
            for font_name in ["SF Pro Text", "Segoe UI", "Helvetica Neue", "Arial"]:
                if font_name in QFontDatabase().families():
                    self.base_font = QFont(font_name)
                    font_loaded = True
                    break

        if not font_loaded:
            self.base_font = QFont("Arial")

    # ---------------- UI ----------------
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.title_label = QLabel("Grooming & Style Tips")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setFont(QFont(self.base_font.family(), 10))
        self.title_label.setStyleSheet("color: white; font-weight: 600;")

        self.suggestion_label = QLabel("")
        self.suggestion_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.suggestion_label.setFont(QFont(self.base_font.family(), 8))
        self.suggestion_label.setStyleSheet("color: #FFD1DC; font-weight: 500;")
        self.suggestion_label.setWordWrap(True)
        self.suggestion_label.setTextFormat(Qt.RichText)

        layout.addWidget(self.title_label)
        layout.addWidget(self.suggestion_label)

    # ---------------- Animations ----------------
    def _setup_animations(self):
        self.opacity_effect = QGraphicsOpacityEffect(self.suggestion_label)
        self.suggestion_label.setGraphicsEffect(self.opacity_effect)

        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_anim.setDuration(600)
        self.fade_anim.finished.connect(self._on_animation_finished)

        self.hold_timer = QTimer(self)
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self._on_hold_timeout)

        # Height animation
        self.resize_anim = QPropertyAnimation(self, b"maximumHeight")
        self.resize_anim.setDuration(400)
        self.resize_anim.setEasingCurve(QEasingCurve.OutCubic)

    # ---------------- Helpers ----------------
    def _calc_hold_time_ms(self, text: str) -> int:
        plain = re.sub("<[^<]+?>", "", text)
        base = 2200
        per_char = 35
        length = len(plain)
        ms = base + per_char * (length // 15)
        return int(max(1800, min(ms, 6000)))

    def _calc_needed_height(self, text: str) -> int:
        """Estimate height needed for text and animate widget to it"""
        font = self.suggestion_label.font()
        metrics = QFontMetrics(font)
        rect = metrics.boundingRect(0, 0, self.width() - 40, 0, Qt.TextWordWrap, text)
        needed = rect.height() + 80  # +title + padding
        return max(self.min_height, min(needed, self.max_height))

    # ---------------- Animation cycle ----------------
    def _start_cycle(self, tips):
        self._tips = tips if tips else ["No suggestions available"]
        self._tip_index = 0
        if not self._cycle_running:
            self._cycle_running = True
            self._fade_in_current()

    def _stop_cycle(self):
        self._cycle_running = False
        self.fade_anim.stop()
        self.hold_timer.stop()

    def _fade_in_current(self):
        if not self._tips:
            return
        text = self._tips[self._tip_index]
        self.suggestion_label.setText(text)

        # Animate flexible height
        target_h = self._calc_needed_height(text)
        self.resize_anim.stop()
        self.resize_anim.setStartValue(self.height())
        self.resize_anim.setEndValue(target_h)
        self.resize_anim.start()

        # Animate opacity
        self.fade_anim.stop()
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self._anim_phase = "in"
        self.fade_anim.start()

    def _fade_out_current(self):
        self.fade_anim.stop()
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self._anim_phase = "out"
        self.fade_anim.start()

    @Slot()
    def _on_animation_finished(self):
        if self._anim_phase == "in":
            cur_text = self._tips[self._tip_index]
            self.hold_timer.start(self._calc_hold_time_ms(cur_text))
        elif self._anim_phase == "out":
            if not self._cycle_running:
                return
            self._tip_index = (self._tip_index + 1) % len(self._tips)
            QTimer.singleShot(200, self._fade_in_current)

    @Slot()
    def _on_hold_timeout(self):
        self._fade_out_current()

    # ---------------- External API ----------------
    def set_suggestion_from_payload(self, payload: dict):
        if not payload or not isinstance(payload, dict):
            return

        tips = []
        if "grooming_tips" in payload:
            tips.append(f"<span style='color:#FFB6C1;'> {payload['grooming_tips']}</span>")
        if "fashion_tips" in payload:
            tips.append(f"<span style='color:#20B2AA;'> {payload['fashion_tips']}</span>")
        if "lighting_tips" in payload:
            tips.append(f"<span style='color:#FFD700;'> {payload['lighting_tips']}</span>")
        if "time_tips" in payload:
            tips.append(f"<span style='color:#87CEFA;'> {payload['time_tips']}</span>")

        if not tips:
            tips = ["<div>No suggestions available</div>"]

        if tips != self._tips:  # restart only if changed
            self._live_mode = True
            self._stop_cycle()
            self._start_cycle(tips)

    def _start_fallback_cycle(self):
        if self._live_mode:
            return
        shuffled = self.suggestions[:]
        random.shuffle(shuffled)
        self._start_cycle(shuffled)

    # ---------------- Paint ----------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 22, 22)
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 40))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 25))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)
        painter.setPen(QColor(255, 255, 255, 60))
        painter.drawPath(path)
