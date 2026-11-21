import requests
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QTextEdit, QGraphicsDropShadowEffect, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QPainter, QPainterPath, QColor, QLinearGradient, QCursor
from PySide6.QtWidgets import QScrollArea, QWidget
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtGui import QPixmap, QPainter


class NewsWidget(QFrame):
    def __init__(self, api_key: str, country: str = "us", update_interval: int = 600000):
        super().__init__()

        self.api_key = api_key
        self.country = country

        # Modern sizing and policies
        self.setMinimumSize(280, 250)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Setup modern styling
        self.setup_fonts()
        self.setup_styling()
        self.add_shadow_effect()
        self.setup_layout()

        # Initial load
        self.load_news()

        # Auto refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_news)
        self.timer.start(update_interval)

    def setup_fonts(self):
        """Setup fonts with fallbacks"""
        font_loaded = False

        # Try to load custom font
        font_paths = [
            "fonts/SF-Pro-Text-Regular.otf",
            "fonts/SF-Pro-Display-Regular.otf",
            "fonts/SF-Pro-Text-Thin.otf"
        ]

        for font_path in font_paths:
            try:
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self.base_font = QFont(families[0])
                        font_loaded = True
                        break
            except:
                continue

        if not font_loaded:
            # Fallback fonts
            fallback_fonts = ["SF Pro Text", "Segoe UI", "Helvetica Neue", "Arial"]
            for font_name in fallback_fonts:
                if font_name in QFontDatabase().families():
                    self.base_font = QFont(font_name)
                    font_loaded = True
                    break

        if not font_loaded:
            self.base_font = QFont("Arial")

    def setup_styling(self):
        """Apply modern glass-morphism styling"""
        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
            }
        """)

    def add_shadow_effect(self):
        """Add drop shadow for depth"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

    def setup_layout(self):
        """Setup the main layout structure"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Modern title with icon
        self.create_title_header(layout)

        # News content area
        self.create_news_content(layout)

    from PySide6.QtSvgWidgets import QSvgWidget

    def create_title_header(self, parent_layout):
        """Create modern title header with icon + text inside one transparent box"""
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtWidgets import QHBoxLayout, QWidget

        header_container = QWidget()
        header_container.setObjectName("headerBox")
        header_container.setStyleSheet("""
            #headerBox {
                background: transparent;
                border: none;
            }
            QLabel {
                color: rgba(255, 255, 255, 0.95);
                font-weight: 500;
            }
        """)

        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(10, 6, 10, 6)
        header_layout.setSpacing(8)

        # Render SVG to pixmap
        svg_renderer = QSvgRenderer("icons/news.svg")
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        svg_renderer.render(painter)
        painter.end()

        icon_label = QLabel()
        icon_label.setPixmap(pixmap)

        self.title = QLabel("Latest News")
        self.title.setFont(QFont(self.base_font.family(), 14, QFont.Medium))

        header_layout.addWidget(icon_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(self.title, 0, Qt.AlignVCenter)

        # ✅ Center the entire header box
        parent_layout.addWidget(header_container, 0, Qt.AlignHCenter)

    def create_news_content(self, parent_layout):
        """Create the news content area with modern styling"""
        self.news_box = QTextEdit()
        self.news_box.setReadOnly(True)
        self.news_box.setFont(QFont(self.base_font.family(), 10, QFont.Normal))
        self.news_box.setCursor(QCursor(Qt.ArrowCursor))

        # Flat text edit styling (no glass background, but keep scrollbar theme)
        self.news_box.setStyleSheet("""
            QTextEdit {
                color: rgba(255, 255, 255, 0.9);
                background: transparent;
                border: none;
                padding: 5px;
                font-weight: 400;
                line-height: 1.4;
            }
            /* Modern Scrollbar Styling */
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(255, 255, 255, 0.7);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: rgba(255, 255, 255, 0.02);
            }
        """)

        parent_layout.addWidget(self.news_box, 1)  # Give it stretch factor

    def paintEvent(self, event):
        """Custom paint event for glass-morphism background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Create rounded rectangle path
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 22, 22)

        # Gradient background
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 38))  # ~15% opacity
        gradient.setColorAt(0.5, QColor(255, 255, 255, 25))  # ~10% opacity
        gradient.setColorAt(1, QColor(255, 255, 255, 20))  # ~8% opacity

        painter.fillPath(path, gradient)

        # Border
        painter.setPen(QColor(255, 255, 255, 51))  # ~20% opacity
        painter.drawPath(path)

        # Inner highlight
        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 21, 21)
        painter.setPen(QColor(255, 255, 255, 76))  # ~30% opacity
        painter.drawPath(inner_path)

    def load_news(self):
        """Fetch and display top headlines with modern formatting"""
        self.title.setText("Loading News...")  # removed 📰

        url = f"https://newsapi.org/v2/top-headlines?country={self.country}&apiKey={self.api_key}"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get("status") == "ok":
                articles = data.get("articles", [])

                if articles:
                    # Format headlines with modern styling
                    formatted_news = self.format_news_articles(articles[:6])
                    self.news_box.setHtml(formatted_news)
                    self.title.setText("Latest News")  # removed 📰
                else:
                    self.show_status("📭 No news available", "info")
            else:
                error_msg = data.get("message", "Unknown error")
                self.show_status(f"⚠️ API Error: {error_msg}", "warning")

        except requests.exceptions.Timeout:
            self.show_status("⏱️ Request timeout", "error")
        except requests.exceptions.ConnectionError:
            self.show_status("🌐 No internet connection", "error")
        except Exception as e:
            self.show_status(f"❌ Error: {str(e)[:50]}...", "error")

    def format_news_articles(self, articles):
        """Format news articles with modern HTML styling"""
        html_content = """
        <style>
            body { 
                font-family: 'SF Pro Text', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 0;
                line-height: 1.5;
            }
            .article {
                margin-bottom: 18px;
                padding-bottom: 15px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .article:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }
            .headline {
                color: rgba(255, 255, 255, 0.95);
                font-size: 11px;
                font-weight: 500;
                margin-bottom: 6px;
                line-height: 1.4;
            }
            .source {
                color: rgba(255, 255, 255, 0.6);
                font-size: 9px;
                font-weight: 400;
                font-style: italic;
            }
            .bullet {
                color: rgba(100, 181, 246, 0.8);
                font-weight: bold;
                margin-right: 8px;
            }
        </style>
        """

        for i, article in enumerate(articles, 1):
            title = article.get('title', 'No title').strip()
            source = article.get('source', {}).get('name', 'Unknown Source')

            # Truncate very long titles
            if len(title) > 120:
                title = title[:117] + "..."

            html_content += f"""
            <div class="article">
                <div class="headline">
                    <span class="bullet">•</span>{title}
                </div>
                <div class="source">{source}</div>
            </div>
            """

        return html_content

    def show_status(self, message, status_type="info"):
        """Show status message with appropriate styling"""
        color_map = {
            "info": "rgba(100, 181, 246, 0.8)",
            "warning": "rgba(255, 193, 7, 0.8)",
            "error": "rgba(244, 67, 54, 0.8)"
        }

        color = color_map.get(status_type, "rgba(255, 255, 255, 0.8)")

        html = f"""
        <div style="
            color: {color};
            font-size: 12px;
            font-weight: 500;
            text-align: center;
            padding: 20px;
            margin-top: 30px;
        ">
            {message}
        </div>
        """

        self.news_box.setHtml(html)
        self.title.setText("Latest News")

    def mousePressEvent(self, event):
        """Manual refresh on click"""
        if event.button() == Qt.LeftButton:
            self.load_news()
        super().mousePressEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    import os

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Test widget
    widget = NewsWidget(
        api_key=os.getenv("NEWS_API_KEY", ""),
        country="us"
    )
    widget.show()

    sys.exit(app.exec())