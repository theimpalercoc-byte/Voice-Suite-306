import sys, cv2, numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QCheckBox, QComboBox, QProgressBar,
    QGroupBox, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from state import shared_state
from video_pipeline import VideoPipelineThread, scan_available_cameras
from audio_engine import AudioPipelineThread
from floating_window import FloatingAvatarWindow
from rigging_canvas import AvatarRiggingWidget

class StudioMasterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI VOICE & AVATAR STUDIO - DGX / OBS BROADCAST")
        self.setMinimumSize(1060, 780)

        self.setStyleSheet("""
            QMainWindow { background-color: #121214; }
            QWidget { color: #E1E1E6; font-family: Segoe UI, sans-serif; }
            QTabWidget::pane { border: 1px solid #29292E; background-color: #121214; }
            QTabBar::tab { background: #202024; color: #A0A0B2; padding: 10px 24px; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background: #00B37E; color: white; }
            QGroupBox { font-weight: bold; border: 2px solid #29292E; border-radius: 10px; margin-top: 14px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
            QComboBox { background-color: #202024; border: 1px solid #29292E; border-radius: 6px; padding: 6px 12px; min-width: 170px; }
            QPushButton { background-color: #00B37E; color: white; font-weight: bold; border: none; border-radius: 8px; padding: 10px 16px; }
            QPushButton:hover { background-color: #00875F; }
            QSlider::groove:horizontal { border: 1px solid #29292E; height: 6px; background: #202024; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00B37E; width: 16px; margin: -5px 0; border-radius: 8px; }
            QProgressBar { border: 1px solid #29292E; border-radius: 5px; text-align: center; background-color: #202024; height: 12px; }
            QProgressBar::chunk { background-color: #00B37E; border-radius: 4px; }
        """)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.studio_tab = QWidget()
        self._build_studio_tab()
        self.tabs.addTab(self.studio_tab, "🎙️ Live Studio & OBS Broadcast")

        self.rigging_widget = AvatarRiggingWidget()
        self.tabs.addTab(self.rigging_widget, "🎯 Avatar Rigging Canvas")

        self.floating_window = FloatingAvatarWindow()

        self.video_thread = VideoPipelineThread()
        self.video_thread.raw_frame_ready.connect(self.on_raw_frame)
        self.video_thread.processed_frame_ready.connect(self.on_processed_frame)
        self.video_thread.face_count_signal.connect(self.on_face_count_update)
        self.video_thread.start()

        self.audio_thread = AudioPipelineThread()
        self.audio_thread.audio_level_signal.connect(self.on_audio_level_update)
        self.audio_thread.start()

    def _build_studio_tab(self):
        layout = QVBoxLayout(self.studio_tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        view_layout = QHBoxLayout()
        in_box = QGroupBox("📷 CAM INPUT & 3D TRACKING (Private View)")
        in_l = QVBoxLayout(in_box)
        self.input_monitor = QLabel("Initializing Camera...")
        self.input_monitor.setFixedSize(440, 330)
        self.input_monitor.setStyleSheet("background-color: #000; border-radius: 8px;")
        self.input_monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        in_l.addWidget(self.input_monitor)
        view_layout.addWidget(in_box)

        out_box = QGroupBox("🎭 CAM OUTPUT (Live Avatar -> OBS)")
        out_l = QVBoxLayout(out_box)
        self.output_monitor = QLabel("Rendering Avatar...")
        self.output_monitor.setFixedSize(440, 330)
        self.output_monitor.setStyleSheet("background-color: #000; border: 2px solid #00B37E; border-radius: 8px;")
        self.output_monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        out_l.addWidget(self.output_monitor)
        view_layout.addWidget(out_box)
        layout.addLayout(view_layout)

        ctrl_layout = QHBoxLayout()
        v_box = QGroupBox("Camera & 3D Motion Controls")
        v_l = QVBoxLayout(v_box)

        # Video Source selection
        v_row = QHBoxLayout()
        v_row.addWidget(QLabel("Source / Camera:"))
        self.v_combo = QComboBox()
        self.rescan_btn = QPushButton("🔄 Rescan")
        self.rescan_btn.setStyleSheet("padding: 6px 10px;")
        self.rescan_btn.clicked.connect(self.populate_camera_list)
        v_row.addWidget(self.v_combo, 3)
        v_row.addWidget(self.rescan_btn, 1)
        v_l.addLayout(v_row)

        # 3D Wireframe and Multi-Person checkboxes
        cb_row = QHBoxLayout()
        self.wf_cb = QCheckBox("📐 Show 3D Tracking Wireframe")
        self.wf_cb.setChecked(True)
        self.wf_cb.toggled.connect(shared_state.toggle_wireframe)
        cb_row.addWidget(self.wf_cb)

        self.mp_cb = QCheckBox("👥 Multi-Person")
        self.mp_cb.toggled.connect(shared_state.toggle_multi_person)
        cb_row.addWidget(self.mp_cb)
        v_l.addLayout(cb_row)

        self.status_lbl = QLabel("Detected Faces: 0 | 3D Rig: Active")
        self.status_lbl.setStyleSheet("color: #00B37E; font-weight: bold;")
        v_l.addWidget(self.status_lbl)

        self.obs_btn = QPushButton("🚀 Toggle Floating OBS Window")
        self.obs_btn.clicked.connect(self.toggle_obs)
        v_l.addWidget(self.obs_btn)
        ctrl_layout.addWidget(v_box, 1)

        a_box = QGroupBox("Voice Lab & Audio Controls")
        a_l = QVBoxLayout(a_box)
        a_row = QHBoxLayout()
        a_row.addWidget(QLabel("Audio Source:"))
        self.a_combo = QComboBox()
        self.a_combo.addItems(["Test Audio File (test_audio.wav)", "Live Microphone"])
        self.a_combo.currentIndexChanged.connect(lambda idx: shared_state.set_audio_source("file", "test_audio.wav") if idx == 0 else shared_state.set_audio_source("mic"))
        a_row.addWidget(self.a_combo)
        a_l.addLayout(a_row)

        self.pitch_lbl = QLabel("Pitch Shift: 0 Semitones")
        a_l.addWidget(self.pitch_lbl)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(0)
        self.pitch_slider.valueChanged.connect(self.on_pitch)
        a_l.addWidget(self.pitch_slider)

        a_l.addWidget(QLabel("Live Audio Level:"))
        self.vu = QProgressBar()
        self.vu.setRange(0, 100)
        a_l.addWidget(self.vu)
        ctrl_layout.addWidget(a_box, 1)
        layout.addLayout(ctrl_layout)

        self.populate_camera_list()
        self.v_combo.currentIndexChanged.connect(self.on_video_selection_changed)

    def populate_camera_list(self):
        self.v_combo.blockSignals(True)
        self.v_combo.clear()
        self.v_combo.addItem("🎬 Test Video File (test_vid.mp4)", ("file", "test_vid.mp4", 0))
        
        cams = scan_available_cameras()
        for c in cams:
            self.v_combo.addItem(f"📷 Camera Device #{c} (Webcam / NVIDIA / OBS)", ("camera", "", c))

        self.v_combo.blockSignals(False)

    def on_video_selection_changed(self, idx):
        data = self.v_combo.currentData()
        if data:
            src_type, path, cam_idx = data
            shared_state.set_video_source(src_type, path, cam_idx)

    def on_raw_frame(self, frame):
        self.input_monitor.setPixmap(self._cv_to_pixmap(frame, 440, 330))

    def on_processed_frame(self, frame):
        self.output_monitor.setPixmap(self._cv_to_pixmap(frame, 440, 330))
        if self.floating_window.isVisible():
            self.floating_window.update_frame(frame)

    def _cv_to_pixmap(self, img, w, h):
        ih, iw, ch = img.shape
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return QPixmap.fromImage(QImage(rgb.data, iw, ih, ch * iw, QImage.Format.Format_RGB888)).scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def on_pitch(self, val):
        self.pitch_lbl.setText(f"Pitch Shift: {val} Semitones")
        shared_state.update_pitch(val)

    def on_face_count_update(self, c):
        self.status_lbl.setText(f"Detected Faces: {c} | 3D Rig: Active")

    def on_audio_level_update(self, lvl):
        self.vu.setValue(min(100, int((lvl / 1200.0) * 100)))

    def toggle_obs(self):
        if self.floating_window.isVisible():
            self.floating_window.hide()
            self.obs_btn.setText("🚀 Launch Floating OBS Window")
        else:
            self.floating_window.show()
            self.obs_btn.setText("⏹️ Close Floating OBS Window")

    def closeEvent(self, e):
        self.video_thread.stop()
        self.audio_thread.stop()
        self.floating_window.close()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudioMasterWindow()
    window.show()
    sys.exit(app.exec())
