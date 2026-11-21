import requests
import random
import os

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QPainterPath, QFont, QFontDatabase, QColor, QLinearGradient
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt


class StocksWidget(QFrame):
    def __init__(self, api_key: str, base_url: str, symbol: str):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.symbol = symbol

        # Size policy
        self.setFixedHeight(180)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # --- 🔹 Apply glass-morphism styling ---
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(2)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Fetch stock data
        history = self.get_stock_history()
        if not history:
            print("⚠️ Using FAKE  Stocks data (Daily limit reached)")
            history = self.generate_fake_data()
        else:
            print("✅ Using REAL Stocks data")
        print("History sample:", history[:5])

        # ✅ Now plot the graph
        self.plot_heartbeat_line(history)

    def paintEvent(self, event):
        """Custom paint event for glass-morphism background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 15, 15)

        # Gradient background (glass effect)
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 38))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 25))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)

        # Outer stroke
        painter.setPen(QColor(255, 255, 255, 51))
        painter.drawPath(path)

        # Inner stroke
        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 14, 14)
        painter.setPen(QColor(255, 255, 255, 76))
        painter.drawPath(inner_path)

    def get_stock_history(self):
        try:
            url = f"{self.base_url}?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol={self.symbol}&apikey={self.api_key}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json().get("Weekly Adjusted Time Series", {})
            dates = sorted(list(data.keys()))[-20:]
            history = [(d, float(data[d]["4. close"])) for d in dates]
            return history
        except Exception as e:
            print(f"Error fetching {self.symbol}: {e}")
            return []

    def generate_fake_data(self):
        return [(f"W{i+1}", 100 + random.randint(-5, 5)) for i in range(20)]

    def plot_heartbeat_line(self, history):
        if not history:
            return

        dates = [d for d, _ in history]
        values = [v for _, v in history]

        # Heartbeat effect
        heartbeat_values = []
        heartbeat_dates = []
        for v, d in zip(values, dates):
            heartbeat_values.append(v)
            heartbeat_values.append(v + random.uniform(-1, 1))
            heartbeat_dates.append(d)
            heartbeat_dates.append(d)

        # Smaller figure
        fig, ax = plt.subplots(figsize=(3, 2), facecolor="none")
        fig.subplots_adjust(left=0.2, right=0.95, top=0.85, bottom=0.25)
        ax.set_facecolor("none")

        # Color
        line_color = (204 / 255, 204 / 255, 204 / 255, 0.6)
        ax.plot(heartbeat_dates, heartbeat_values, color=line_color, linewidth=0.8)

        # Axis styling
        ax.spines["top"].set_alpha(0)
        ax.spines["right"].set_alpha(0)
        ax.spines["bottom"].set_color("white")
        ax.spines["bottom"].set_alpha(0.3)
        ax.spines["left"].set_color("white")
        ax.spines["left"].set_alpha(0.3)

        # Ticks
        ax.tick_params(axis="x", colors="white", labelrotation=30, labelsize=3, length=2, width=0.5)
        ax.tick_params(axis="y", colors="white", labelsize=3, length=2, width=0.5)

        # Grid
        ax.grid(True, color='white', alpha=0.15, linestyle='--', linewidth=0.5)

        # Fewer X labels
        num_labels = 4
        tick_indices = list(range(0, len(heartbeat_dates), max(1, len(heartbeat_dates) // num_labels)))
        ax.set_xticks([heartbeat_dates[i] for i in tick_indices])
        ax.set_xticklabels([dates[i // 2] for i in tick_indices], color="white", fontsize=4)

        # Y-axis labels
        min_y, max_y = min(values), max(values)
        y_ticks = [min_y + (max_y - min_y) * i / 4 for i in range(5)]
        ax.set_yticks(y_ticks)
        ax.set_yticklabels([f"{v:.1f}" for v in y_ticks], color="white", fontsize=4)

        ax.grid(False)

        # Embed the matplotlib canvas
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background: transparent;")
        self.layout.addWidget(canvas)

        # Label
        label = QLabel(f"{self.symbol} Weekly Trend")
        label.setStyleSheet("""
            color: rgba(204, 204, 204, 0.8);
            font-size: 12px;
            font-weight: bold;
            margin-top: -3px;
        """)
        label.setAlignment(Qt.AlignCenter)

        # Load and apply SF Pro font (if exists)
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "SF-Pro-Display-Regular.otf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                sf_pro_font = QFont(families[0], 10)
                label.setFont(sf_pro_font)

        self.layout.addWidget(label)
