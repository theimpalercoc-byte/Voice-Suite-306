import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPainterPath

class FloatingAvatarWindow(QWidget):
    """Clean, borderless window designed exclusively for OBS Window Capture."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OBS_AVATAR_CAPTURE_SURFACE")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 360)
        self.drag_position = QPoint()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_surface = QLabel(self)
        self.video_surface.setStyleSheet(
            "background-color: #121214; border: 2px solid #00B37E; border-radius: 20px;"
        )
        self.video_surface.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_surface)

    def update_frame(self, cv_img: np.ndarray):
        height, width, channel = cv_img.shape
        bytes_per_line = channel * width
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        
        qt_img = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.video_surface.width(), self.video_surface.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Apply rounded corner clipping
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 20, 20)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        self.video_surface.setPixmap(rounded)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
