from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, \
    QGraphicsDropShadowEffect, QSizePolicy
from PySide6.QtCore import Qt, QDate, QTimer, Signal
from PySide6.QtGui import QFontDatabase, QFont, QPainter, QPainterPath, QColor, QLinearGradient, QCursor
import os
import calendar


class ModernCalendar(QWidget):
    # Signal emitted when a date is clicked
    dateClicked = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Widget properties - Made smaller and more compact
        self.setMinimumSize(200, 220)  # Reduced from 280x350
        self.setMaximumWidth(200)      # Reduced from 280
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # Date tracking
        self.current_date = QDate.currentDate()
        self.display_year = self.current_date.year()
        self.display_month = self.current_date.month()
        self.selected_date = self.current_date
        self.marked_dates = set()  # Track marked dates

        # Setup components
        self.setup_fonts()
        self.setup_styling()
        self.add_shadow_effect()
        self.setup_layout()
        self.populate_dates()

        # Auto-update timer for current day highlighting
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_date_update)
        self.update_timer.start(60000)  # Check every minute

    def setup_fonts(self):
        """Setup fonts with fallbacks"""
        font_loaded = False

        # Try to load custom font
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "SF-Pro-Text-Thin.otf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                self.base_font = QFont(font_family)
                font_loaded = True

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
            QWidget {
                background: transparent;
                border: none;
            }
        """)

    def add_shadow_effect(self):
        """Add drop shadow for depth"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)  # Reduced from 25
        shadow.setColor(QColor(0, 0, 0, 80))  # Reduced opacity
        shadow.setOffset(0, 8)  # Reduced from 10
        self.setGraphicsEffect(shadow)

    def setup_layout(self):
        """Create the main layout structure"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)  # Reduced from 20
        main_layout.setSpacing(12)  # Reduced from 15

        # Header section with navigation
        self.create_header(main_layout)

        # Calendar grid
        self.create_calendar_grid(main_layout)

        main_layout.addStretch()

    def create_header(self, parent_layout):
        """Create header with month/year and navigation"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)  # Reduced from 10
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Previous month button
        self.prev_button = self.create_nav_button("‹")
        self.prev_button.clicked.connect(self.previous_month)
        header_layout.addWidget(self.prev_button)

        # Add some spacing to prevent overlap
        header_layout.addSpacing(5)

        # Month and year display
        self.month_year_label = QLabel()
        self.month_year_label.setAlignment(Qt.AlignCenter)
        self.month_year_label.setFont(QFont(self.base_font.family(), 11, QFont.Medium))  # Reduced from 12
        self.month_year_label.setWordWrap(True)  # Enable text wrapping
        self.month_year_label.setMinimumWidth(100)  # Ensure minimum width
        self.month_year_label.setMaximumWidth(120)  # Prevent overflow
        self.month_year_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.month_year_label.setStyleSheet("""
            color: white;
            font-weight: 500;
            padding: 4px;
            text-align: center;
        """)
        self.update_month_year_display()
        header_layout.addWidget(self.month_year_label, 1)

        # Add some spacing to prevent overlap
        header_layout.addSpacing(5)

        # Next month button
        self.next_button = self.create_nav_button("›")
        self.next_button.clicked.connect(self.next_month)
        header_layout.addWidget(self.next_button)

        parent_layout.addLayout(header_layout)

    def create_nav_button(self, text):
        """Create navigation button with hover effects"""
        button = QPushButton(text)
        button.setFixedSize(26, 26)  # Reduced from 30x30
        button.setFont(QFont(self.base_font.family(), 12, QFont.Bold))  # Reduced from 14
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 13px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.35);
            }
        """)
        return button

    def create_calendar_grid(self, parent_layout):
        """Create the calendar grid layout"""
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(0)
        self.grid.setContentsMargins(0, 0, 0, 0)

        # Day headers aligned with dates
        day_names = ["M", "T", "W", "T", "F", "S", "S"]
        for col, day_name in enumerate(day_names):
            header_label = QLabel(day_name)
            header_label.setAlignment(Qt.AlignCenter)
            header_label.setFont(QFont(self.base_font.family(), 8, QFont.Medium))  # Reduced from 9
            header_label.setFixedSize(28, 22)   # Reduced from 40x25
            header_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.8);
                font-weight: 500;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            """)
            self.grid.addWidget(header_label, 0, col)

        parent_layout.addWidget(self.grid_widget)

    def create_date_label(self, day, is_current_month=True, is_today=False, is_selected=False, is_marked=False):
        """Create a styled date label"""
        label = ClickableLabel(str(day))
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont(self.base_font.family(), 8, QFont.Normal))  # Reduced from 9
        label.setFixedSize(28, 28)  # Reduced from 40x40
        label.setCursor(QCursor(Qt.PointingHandCursor))

        # Connect click signal
        date_obj = QDate(self.display_year, self.display_month, day)
        label.clicked.connect(lambda: self.on_date_clicked(date_obj))

        # Apply styling based on state priority: today > selected > marked > regular
        if is_today:
            label.setStyleSheet("""
                ClickableLabel {
                    background: rgba(255, 255, 255, 0.15);
                    border: 2px solid rgba(255, 255, 255, 0.25);
                    border-radius: 14px;
                    color: white;
                    font-weight: bold;
                }
                ClickableLabel:hover {
                    background: rgba(255, 255, 255, 0.25);
                    border: 2px solid rgba(255, 255, 255, 0.35);
                }
            """)
        elif is_selected:
            label.setStyleSheet("""
                ClickableLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(100, 181, 246, 0.8),
                        stop:1 rgba(33, 150, 243, 0.8));
                    border: 2px solid rgba(100, 181, 246, 0.6);
                    border-radius: 14px;
                    color: white;
                    font-weight: bold;
                }
                ClickableLabel:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(100, 181, 246, 0.9),
                        stop:1 rgba(33, 150, 243, 0.9));
                }
            """)
        elif is_marked:
            label.setStyleSheet("""
                ClickableLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(33, 150, 243, 0.6),
                        stop:1 rgba(21, 101, 192, 0.6));
                    border: 2px solid rgba(33, 150, 243, 0.8);
                    border-radius: 14px;
                    color: white;
                    font-weight: 600;
                }
                ClickableLabel:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(33, 150, 243, 0.8),
                        stop:1 rgba(21, 101, 192, 0.8));
                    border: 2px solid rgba(33, 150, 243, 1.0);
                }
            """)
        elif is_current_month:
            label.setStyleSheet("""
                ClickableLabel {
                    background: transparent;
                    border: none;
                    color: rgba(255, 255, 255, 0.9);
                    font-weight: 400;
                }
                ClickableLabel:hover {
                    background: transparent;
                    border: none;
                    color: white;
                    font-weight: 500;
                }
            """)
        else:
            label.setStyleSheet("""
                ClickableLabel {
                    background: transparent;
                    border: none;
                    color: rgba(255, 255, 255, 0.3);
                    font-weight: 300;
                }
                ClickableLabel:hover {
                    background: rgba(255, 255, 255, 0.05);
                    color: rgba(255, 255, 255, 0.5);
                }
            """)

        return label

    def populate_dates(self):
        """Populate the calendar grid with dates"""
        # Clear existing date labels (keep headers)
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget():
                row, col, _, _ = self.grid.getItemPosition(i)
                if row > 0:  # Keep headers
                    item.widget().setParent(None)

        cal = calendar.Calendar(0)  # Monday as first day
        month_dates = list(cal.itermonthdates(self.display_year, self.display_month))

        today = QDate.currentDate()
        row, col = 1, 0

        for date in month_dates:
            day = date.day
            is_current_month = date.month == self.display_month
            is_today = (date == today.toPython())
            is_selected = (date == self.selected_date.toPython())
            is_marked = (date in self.marked_dates)

            label = self.create_date_label(day, is_current_month, is_today, is_selected, is_marked)
            self.grid.addWidget(label, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

    def update_month_year_display(self):
        """Update the month/year header display with smart text wrapping"""
        month_name = QDate(2000, self.display_month, 1).toString("MMMM")
        year_str = str(self.display_year)
        
        # Check if the full month name + year would be too long
        full_text = f"{month_name} {year_str}"
        
        # Use font metrics to check text width
        font_metrics = self.month_year_label.fontMetrics()
        text_width = font_metrics.horizontalAdvance(full_text)
        available_width = 120  # Maximum width we set for the label
        
        if text_width > available_width:
            # Use abbreviated month name for long months
            abbreviated_month = QDate(2000, self.display_month, 1).toString("MMM")
            self.month_year_label.setText(f"{abbreviated_month} {year_str}")
        else:
            # Use full month name if it fits
            self.month_year_label.setText(full_text)

    def previous_month(self):
        if self.display_month == 1:
            self.display_month, self.display_year = 12, self.display_year - 1
        else:
            self.display_month -= 1
        self.update_month_year_display()
        self.populate_dates()

    def next_month(self):
        if self.display_month == 12:
            self.display_month, self.display_year = 1, self.display_year + 1
        else:
            self.display_month += 1
        self.update_month_year_display()
        self.populate_dates()

    def on_date_clicked(self, date):
        self.selected_date = date
        self.populate_dates()
        self.dateClicked.emit(date)

    def mark_date(self, date):
        """Mark a date with blue circle indicator"""
        if isinstance(date, QDate):
            self.marked_dates.add(date.toPython())
        else:
            self.marked_dates.add(date)
        self.populate_dates()

    def unmark_date(self, date):
        """Remove mark from a date"""
        if isinstance(date, QDate):
            date_py = date.toPython()
        else:
            date_py = date
        self.marked_dates.discard(date_py)
        self.populate_dates()

    def toggle_mark_date(self, date):
        """Toggle mark on a date"""
        if isinstance(date, QDate):
            date_py = date.toPython()
        else:
            date_py = date
        
        if date_py in self.marked_dates:
            self.unmark_date(date)
        else:
            self.mark_date(date)

    def check_date_update(self):
        current = QDate.currentDate()
        if current != self.current_date:
            self.current_date = current
            self.populate_dates()

    def paintEvent(self, event):
        """Custom paint event for glass-morphism background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        path.addRoundedRect(rect, 20, 20)  # Reduced corner radius from 25

        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 38))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 25))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)

        painter.setPen(QColor(255, 255, 255, 51))
        painter.drawPath(path)

        inner_rect = rect.adjusted(1, 1, -1, -1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 19, 19)
        painter.setPen(QColor(255, 255, 255, 76))
        painter.drawPath(inner_path)


class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    calendar_widget = ModernCalendar()
    calendar_widget.dateClicked.connect(lambda d: print(f"Selected date: {d.toString()}"))
    calendar_widget.show()
    sys.exit(app.exec())