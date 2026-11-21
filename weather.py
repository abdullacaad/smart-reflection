import os
import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QFontMetrics


class WeatherWidget(QWidget):
    def __init__(self, api_key, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.city = "London"

        # Compact widget size
        self.setMinimumSize(180, 140)
        self.setStyleSheet("background: transparent;")

        self.setup_ui()
        self.fetch_weather()

        # Refresh every 30 minutes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_weather)
        self.timer.start(1800000)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)

        # Top row: icon + temperature
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        # Weather icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(60, 60)
        self.icon_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        top_layout.addWidget(self.icon_label, 0, Qt.AlignLeft)

        # Temperature container (horizontal: temp + °F)
        temp_layout = QHBoxLayout()
        temp_layout.setSpacing(2)
        temp_layout.setContentsMargins(0, 0, 0, 0)

        self.temp_label = QLabel("--°")
        self.temp_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.temp_label.setStyleSheet("color: white;")
        self.temp_label.setFont(QFont("SF-Pro-Display-Thin", 44,))

        self.temp_f_label = QLabel("--°F")
        self.temp_f_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.temp_f_label.setFont(QFont("SF-Pro-Text-Thin", 14))
        self.temp_f_label.setStyleSheet("color: rgba(255,255,255,0.7); padding-top: 6px;")

        temp_layout.addWidget(self.temp_label, 0, Qt.AlignVCenter)
        temp_layout.addWidget(self.temp_f_label, 0, Qt.AlignTop)

        top_layout.addLayout(temp_layout)
        layout.addLayout(top_layout)

        # City name
        self.city_label = QLabel(self.city)
        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_label.setFont(QFont("SF-Pro-Text-Thin", 14, QFont.Bold))
        self.city_label.setStyleSheet("color: white;")
        layout.addWidget(self.city_label)

        # Weather description
        self.desc_label = QLabel("Clear Sky")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setFont(QFont("SF-Pro-Text-Thin", 11))
        self.desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        layout.addWidget(self.desc_label)

        # Humidity info
        self.humidity_label = QLabel("Humidity: --%")
        self.humidity_label.setAlignment(Qt.AlignCenter)
        self.humidity_label.setFont(QFont("SF-Pro-Text-Thin", 10))
        self.humidity_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        layout.addWidget(self.humidity_label)

        layout.addStretch()

    def adjust_temp_font(self):
        """Dynamically resize temperature font"""
        if not self.temp_label.text():
            return

        available_width = self.temp_label.width()
        available_height = self.temp_label.height()

        font = self.temp_label.font()
        size = 40
        font.setPointSize(size)
        metrics = QFontMetrics(font)

        while (metrics.horizontalAdvance(self.temp_label.text()) > available_width or
               metrics.height() > available_height) and size > 10:
            size -= 1
            font.setPointSize(size)
            metrics = QFontMetrics(font)

        self.temp_label.setFont(font)

    def fetch_weather(self):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.update_weather_display(data)
            else:
                self.show_error("API error")
        except Exception as e:
            print(f"Weather fetch error: {e}")
            self.show_error("Connection error")

    def update_weather_display(self, data):
        try:
            # Temps
            temp_c = int(data['main']['temp'])
            temp_f = int(temp_c * 9 / 5 + 32)
            self.temp_label.setText(f"{temp_c}°")
            self.temp_f_label.setText(f"{temp_f}°F")
            self.adjust_temp_font()

            # City
            self.city_label.setText(self.city)

            # Description + humidity
            description = data['weather'][0]['description'].title()
            self.desc_label.setText(description)
            humidity = data['main']['humidity']
            self.humidity_label.setText(f"Humidity: {humidity}%")

            # Icon
            icon_code = data['weather'][0]['icon']
            self.load_weather_icon(icon_code)
        except Exception as e:
            print(f"Weather parse error: {e}")
            self.show_error("Data error")

    def load_weather_icon(self, icon_code):
        ICON_MAP = {
            "01d": "clear_day.svg", "01n": "clear_night.svg",
            "02d": "few_clouds_day.svg", "02n": "few_clouds_night.svg",
            "03d": "clouds.svg", "03n": "clouds.svg",
            "04d": "broken_clouds.svg", "04n": "broken_clouds.svg",
            "09d": "shower_rain.svg", "09n": "shower_rain.svg",
            "10d": "rain_day.svg", "10n": "rain_night.svg",
            "11d": "thunderstorm.svg", "11n": "thunderstorm.svg",
            "13d": "snow.svg", "13n": "snow.svg",
            "50d": "mist.svg", "50n": "mist.svg",
        }

        try:
            filename = ICON_MAP.get(icon_code, "default.svg")
            icon_path = os.path.join(os.path.dirname(__file__), "icons", filename)

            if os.path.exists(icon_path):
                svg_widget = QSvgWidget(icon_path)
                svg_widget.setFixedSize(60, 60)
                self.icon_label.setPixmap(QPixmap())  # clear old
                layout = self.icon_label.parentWidget().layout()
                layout.replaceWidget(self.icon_label, svg_widget)
                self.icon_label.deleteLater()
                self.icon_label = svg_widget
            else:
                self.icon_label.setPixmap(self.create_default_icon())
        except Exception as e:
            print(f"Icon error: {e}")
            self.icon_label.setPixmap(self.create_default_icon())

    def create_default_icon(self):
        pixmap = QPixmap(50, 50)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(15, 15, 20, 20)
        painter.end()
        return pixmap

    def show_error(self, message):
        self.temp_label.setText("--°")
        self.temp_f_label.setText("--°F")
        self.desc_label.setText(message)
        self.humidity_label.setText("")
        self.icon_label.setPixmap(self.create_default_icon())
