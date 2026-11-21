import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from datetime import datetime
from PySide6.QtSvgWidgets import QSvgWidget   # direct SVG widget


class TimeWidget(QFrame):
    def __init__(self, update_interval: int = 1000):
        super().__init__()

        # --- Base directory (same trick as main.py) ---
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.calendar_svg_path = os.path.join(BASE_DIR, "icons", "calendar.svg")

        # --- Debug: confirm file exists ---
        print("Calendar exists:", os.path.exists(self.calendar_svg_path))

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border-radius: 15px;
                padding: 5px;
            }
            QLabel {
                color: white;
            }
            QLabel#Time {
                font-size: 76px;
                font-weight: bold;
                margin-bottom: -8px;
            }
            QLabel#Day {
                font-size: 26px;
                font-weight: 500;
                margin-bottom: -4px;
            }
            QLabel#Date {
                font-size: 18px;
            }
        """)

        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        # Time
        self.time_label = QLabel("--:--")
        self.time_label.setObjectName("Time")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

        # Day
        self.day_label = QLabel("------")
        self.day_label.setObjectName("Day")
        self.day_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.day_label)

        # Date Row (icon + text)
        date_row = QHBoxLayout()
        date_row.setSpacing(4)
        date_row.setContentsMargins(2, 0, 0, 0)

        # Calendar SVG icon
        self.calendar_icon = QSvgWidget(self.calendar_svg_path)
        self.calendar_icon.setFixedSize(16, 16)   # small size
        date_row.addWidget(self.calendar_icon)

        # Date label
        self.date_label = QLabel("-- ---- -- ----")
        self.date_label.setObjectName("Date")
        self.date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        date_row.addWidget(self.date_label)

        layout.addLayout(date_row)
        layout.addStretch(3)

        # Timer
        self.update_time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(update_interval)

    def update_time(self):
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M"))
        self.day_label.setText(now.strftime("%A"))
        self.date_label.setText(now.strftime("%B %d, %Y"))
