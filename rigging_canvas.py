import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsPixmapItem, QLabel, QFileDialog, QGraphicsItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QColor, QPen, QBrush, QFont
from state import shared_state

class CalibrationPin(QGraphicsEllipseItem):
    """An interactive, draggable anchor pin for calibrating facial features."""
    def __init__(self, label: str, color_hex: str, x: float, y: float, radius: float = 9):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.label = label
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(color_hex)))
        self.setPen(QPen(QColor("#FFFFFF"), 2))
        
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{label} Anchor")

class AvatarRiggingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pins = {}
        self.bg_item = None
        self.current_image_path = "avatars/default_avatar.png"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Info
        info = QLabel("🎯 Drag the 5 marker pins to match the eyes, nose, and mouth corners:")
        info.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        info.setStyleSheet("color: #E1E1E6;")
        layout.addWidget(info)

        # Graphics Scene & View Canvas
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("background-color: #1A1A1E; border: 2px solid #29292E; border-radius: 8px;")
        self.view.setFixedSize(510, 510)
        layout.addWidget(self.view, alignment=Qt.AlignmentFlag.AlignCenter)

        # Control Buttons
        btn_row = QHBoxLayout()
        self.load_btn = QPushButton("📂 Load Avatar Image")
        self.load_btn.clicked.connect(self.browse_avatar)
        btn_row.addWidget(self.load_btn)

        self.reset_btn = QPushButton("🔄 Reset Pins")
        self.reset_btn.clicked.connect(self.reset_pins)
        btn_row.addWidget(self.reset_btn)

        self.lock_btn = QPushButton("🔒 Lock & Apply Rig")
        self.lock_btn.setStyleSheet("background-color: #3182CE; color: white; font-weight: bold; border-radius: 8px; padding: 10px;")
        self.lock_btn.clicked.connect(self.lock_and_export_calibration)
        btn_row.addWidget(self.lock_btn)

        layout.addLayout(btn_row)

        # Status readout
        self.status_lbl = QLabel("Rig Status: Default alignment active.")
        self.status_lbl.setStyleSheet("color: #00B37E; font-weight: bold;")
        layout.addWidget(self.status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # Load default template
        self.load_avatar_image(self.current_image_path)

    def load_avatar_image(self, path: str):
        if not os.path.exists(path):
            return

        self.current_image_path = path
        self.scene.clear()
        self.pins.clear()

        pixmap = QPixmap(path).scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(0, 0, 500, 500)

        # Populate the 5 key facial anchors
        current_pins = shared_state.get_pins()
        self.pins["Left Eye"] = CalibrationPin("Left Eye", "#E53E3E", *current_pins["Left Eye"])
        self.pins["Right Eye"] = CalibrationPin("Right Eye", "#E53E3E", *current_pins["Right Eye"])
        self.pins["Nose Tip"] = CalibrationPin("Nose Tip", "#ECC94B", *current_pins["Nose Tip"])
        self.pins["Mouth Left"] = CalibrationPin("Mouth Left", "#3182CE", *current_pins["Mouth Left"])
        self.pins["Mouth Right"] = CalibrationPin("Mouth Right", "#3182CE", *current_pins["Mouth Right"])

        for pin in self.pins.values():
            self.scene.addItem(pin)

    def browse_avatar(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Character Image", "avatars", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.load_avatar_image(file_path)
            self.status_lbl.setText(f"Loaded: {os.path.basename(file_path)}")

    def reset_pins(self):
        default_coords = {
            "Left Eye": (180.0, 200.0),
            "Right Eye": (320.0, 200.0),
            "Nose Tip": (250.0, 270.0),
            "Mouth Left": (190.0, 360.0),
            "Mouth Right": (310.0, 360.0),
        }
        for name, pin in self.pins.items():
            pin.setPos(*default_coords[name])
        self.status_lbl.setText("Pins reset to initial defaults.")

    def lock_and_export_calibration(self):
        coords = {}
        for name, pin in self.pins.items():
            pos = pin.scenePos()
            coords[name] = (round(pos.x(), 1), round(pos.y(), 1))

        # Synchronize with global shared_state
        shared_state.update_pins(coords)
        self.status_lbl.setText("✅ Rig Locked! Calibration exported to LivePortrait matrix.")
        print("\n=== LivePortrait Calibration Map Exported ===")
        for k, v in coords.items():
            print(f"  {k}: X={v[0]}, Y={v[1]}")
