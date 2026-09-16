import sys, os, cv2, numpy as np, urllib.request
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QCheckBox, QComboBox, QProgressBar,
    QGroupBox, QTabWidget, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont

from state import shared_state
from video_pipeline import VideoPipelineThread, scan_available_cameras
from audio_engine import AudioPipelineThread
from floating_window import FloatingAvatarWindow
from rigging_canvas import AvatarRiggingWidget

MODELS_INFO = {
    "LivePortrait Appearance": ("weights/appearance_feature_extractor.pth", "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/appearance_feature_extractor.pth"),
    "LivePortrait Motion": ("weights/motion_extractor.pth", "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/motion_extractor.pth"),
    "LivePortrait Spade Gen": ("weights/spade_generator.pth", "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/spade_generator.pth"),
    "LivePortrait Warping": ("weights/warping_spade.pth", "https://huggingface.co/KwaiVGI/LivePortrait/resolve/main/warping_spade.pth"),
}

class DownloadWorker(QThread):
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal()

    def run(self):
        os.makedirs("weights", exist_ok=True)
        for name, (path, url) in MODELS_INFO.items():
            if not os.path.exists(path) or os.path.getsize(path) < 1000:
                self.progress_signal.emit(f"Downloading {name}...", 10)
                try:
                    urllib.request.urlretrieve(url, path)
                    self.progress_signal.emit(f"✓ Completed {name}", 100)
                except Exception as e:
                    self.progress_signal.emit(f"Failed {name}: {e}", 0)
        self.finished_signal.emit()

class StudioMasterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VOICE SUITE 306 - BROADCAST MASTER STUDIO")
        self.setMinimumSize(1120, 820)

        self.setStyleSheet("""
            QMainWindow { background-color: #121214; }
            QWidget { color: #E1E1E6; font-family: Segoe UI, sans-serif; }
            QTabWidget::pane { border: 1px solid #29292E; background-color: #121214; }
            QTabBar::tab { background: #202024; color: #A0A0B2; padding: 12px 26px; font-weight: bold; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background: #00B37E; color: white; }
            QGroupBox { font-weight: bold; border: 2px solid #29292E; border-radius: 10px; margin-top: 14px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
            QComboBox { background-color: #202024; border: 1px solid #29292E; border-radius: 6px; padding: 6px 12px; min-width: 170px; }
            QPushButton { background-color: #00B37E; color: white; font-weight: bold; border: none; border-radius: 8px; padding: 10px 16px; }
            QPushButton:hover { background-color: #00875F; }
            QSlider::groove:horizontal { border: 1px solid #29292E; height: 6px; background: #202024; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00B37E; width: 16px; margin: -5px 0; border-radius: 8px; }
            QProgressBar { border: 1px solid #29292E; border-radius: 5px; text-align: center; background-color: #202024; height: 14px; }
            QProgressBar::chunk { background-color: #00B37E; border-radius: 4px; }
        """)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Live Broadcast
        self.studio_tab = QWidget()
        self._build_studio_tab()
        self.tabs.addTab(self.studio_tab, "📷 Live Broadcast Studio")

        # Tab 2: Voice Lab
        self.voice_tab = QWidget()
        self._build_voice_tab()
        self.tabs.addTab(self.voice_tab, "🎙️ Voice Lab & DSP Engine")

        # Tab 3: Rigging Canvas
        self.rigging_widget = AvatarRiggingWidget()
        self.tabs.addTab(self.rigging_widget, "🎯 Avatar Rigging Canvas")

        # Tab 4: Model Manager
        self.model_tab = QWidget()
        self._build_model_tab()
        self.tabs.addTab(self.model_tab, "⬇️ AI Model Manager")

        self.floating_window = FloatingAvatarWindow()

        # Threads
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

        view_layout = QHBoxLayout()
        in_box = QGroupBox("📷 CAM INPUT & 3D MESH (Private Streamer View)")
        in_l = QVBoxLayout(in_box)
        self.input_monitor = QLabel("Initializing Camera...")
        self.input_monitor.setFixedSize(450, 335)
        self.input_monitor.setStyleSheet("background-color: #000; border-radius: 8px;")
        self.input_monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        in_l.addWidget(self.input_monitor)
        view_layout.addWidget(in_box)

        out_box = QGroupBox("🎭 CAM OUTPUT (Live Avatar Broadcasting to OBS)")
        out_l = QVBoxLayout(out_box)
        self.output_monitor = QLabel("Rendering Avatar...")
        self.output_monitor.setFixedSize(450, 335)
        self.output_monitor.setStyleSheet("background-color: #000; border: 2px solid #00B37E; border-radius: 8px;")
        self.output_monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        out_l.addWidget(self.output_monitor)
        view_layout.addWidget(out_box)
        layout.addLayout(view_layout)

        # Controls
        ctrl_box = QGroupBox("Video Device & Mocap Tracking Settings")
        c_layout = QGridLayout(ctrl_box)

        c_layout.addWidget(QLabel("Video Capture Source:"), 0, 0)
        self.v_combo = QComboBox()
        c_layout.addWidget(self.v_combo, 0, 1)

        self.rescan_btn = QPushButton("🔄 Rescan All Devices")
        self.rescan_btn.clicked.connect(self.populate_camera_list)
        c_layout.addWidget(self.rescan_btn, 0, 2)

        self.wf_cb = QCheckBox("📐 Overlay 3D Tracking Wireframe")
        self.wf_cb.setChecked(True)
        self.wf_cb.toggled.connect(shared_state.toggle_wireframe)
        c_layout.addWidget(self.wf_cb, 1, 0)

        self.mp_cb = QCheckBox("👥 Multi-Person Tracking Mode")
        self.mp_cb.toggled.connect(shared_state.toggle_multi_person)
        c_layout.addWidget(self.mp_cb, 1, 1)

        self.status_lbl = QLabel("3D Tracking: Active")
        self.status_lbl.setStyleSheet("color: #00B37E; font-weight: bold;")
        c_layout.addWidget(self.status_lbl, 1, 2)

        self.obs_btn = QPushButton("🚀 Toggle Floating OBS Window")
        self.obs_btn.clicked.connect(self.toggle_obs)
        c_layout.addWidget(self.obs_btn, 2, 0, 1, 3)

        layout.addWidget(ctrl_box)
        self.populate_camera_list()
        self.v_combo.currentIndexChanged.connect(self.on_video_selection_changed)

    def _build_voice_tab(self):
        layout = QVBoxLayout(self.voice_tab)
        layout.setContentsMargins(20, 20, 20, 20)

        # Voice Model Dropdown
        vm_box = QGroupBox("Voice Conversion Neural Network Model")
        vm_l = QHBoxLayout(vm_box)
        self.vm_combo = QComboBox()
        self.scan_voice_models()
        self.vm_refresh_btn = QPushButton("🔄 Refresh Voices Folder")
        self.vm_refresh_btn.clicked.connect(self.scan_voice_models)
        vm_l.addWidget(self.vm_combo, 3)
        vm_l.addWidget(self.vm_refresh_btn, 1)
        layout.addWidget(vm_box)

        # FX Knobs / Sliders
        fx_box = QGroupBox("Tone, Sound FX & Dynamics")
        fx_l = QGridLayout(fx_box)

        self.p_slider, self.p_lbl = self._create_slider("Pitch Shift (Semitones)", -12, 12, 0)
        self.r_slider, self.r_lbl = self._create_slider("Reverb Intensity (%)", 0, 100, 0)
        self.e_slider, self.e_lbl = self._create_slider("Echo Delay (%)", 0, 100, 0)
        self.g_slider, self.g_lbl = self._create_slider("Noise Gate Threshold", 0, 100, 20)

        fx_l.addWidget(self.p_lbl, 0, 0); fx_l.addWidget(self.p_slider, 0, 1)
        fx_l.addWidget(self.r_lbl, 1, 0); fx_l.addWidget(self.r_slider, 1, 1)
        fx_l.addWidget(self.e_lbl, 2, 0); fx_l.addWidget(self.e_slider, 2, 1)
        fx_l.addWidget(self.g_lbl, 3, 0); fx_l.addWidget(self.g_slider, 3, 1)
        layout.addWidget(fx_box)

        # Sync & Level
        meter_box = QGroupBox("Live Signal & Lip-Sync Buffer")
        m_l = QVBoxLayout(meter_box)
        m_l.addWidget(QLabel("Live Audio Level (RMS):"))
        self.vu = QProgressBar()
        self.vu.setRange(0, 100)
        m_l.addWidget(self.vu)
        layout.addWidget(meter_box)

    def _build_model_tab(self):
        layout = QVBoxLayout(self.model_tab)
        layout.setContentsMargins(20, 20, 20, 20)

        box = QGroupBox("Hugging Face Neural Network Weights")
        b_layout = QVBoxLayout(box)

        info = QLabel("Download pre-trained weights for LivePortrait face reenactment and voice models:")
        info.setFont(QFont("Segoe UI", 11))
        b_layout.addWidget(info)

        self.model_status_labels = {}
        for name, (path, _) in MODELS_INFO.items():
            status = "✓ Installed" if os.path.exists(path) else "❌ Missing"
            color = "#00B37E" if "✓" in status else "#E23E44"
            lbl = QLabel(f"• {name}: {status}")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
            b_layout.addWidget(lbl)
            self.model_status_labels[name] = lbl

        self.dl_prog_lbl = QLabel("Status: Idle")
        b_layout.addWidget(self.dl_prog_lbl)

        self.dl_btn = QPushButton("⬇️ Download All Models from Hugging Face")
        self.dl_btn.setStyleSheet("background-color: #3182CE; padding: 12px; font-size: 14px;")
        self.dl_btn.clicked.connect(self.start_download)
        b_layout.addWidget(self.dl_btn)

        layout.addWidget(box)

    def _create_slider(self, name, min_v, max_v, def_v):
        lbl = QLabel(f"{name}: {def_v}")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(def_v)
        slider.valueChanged.connect(lambda val: (lbl.setText(f"{name}: {val}"), self.update_fx_state()))
        return slider, lbl

    def update_fx_state(self):
        shared_state.update_fx(self.p_slider.value(), self.r_slider.value(), self.e_slider.value(), self.g_slider.value())

    def scan_voice_models(self):
        self.vm_combo.clear()
        self.vm_combo.addItem("DSP Passthrough (Natural / Pitch FX)")
        os.makedirs("voices", exist_ok=True)
        for f in os.listdir("voices"):
            if f.endswith((".onnx", ".pth")):
                self.vm_combo.addItem(f"AI Voice: {f}")

    def populate_camera_list(self):
        self.v_combo.blockSignals(True)
        self.v_combo.clear()
        self.v_combo.addItem("🎬 Test Video File (test_vid.mp4)", ("file", "test_vid.mp4", 0))
        cams = scan_available_cameras(8)
        for c in cams:
            self.v_combo.addItem(f"📷 Camera Device #{c} (Integrated / USB / NVIDIA / OBS)", ("camera", "", c))
        self.v_combo.blockSignals(False)

    def on_video_selection_changed(self, idx):
        data = self.v_combo.currentData()
        if data:
            src_type, path, cam_idx = data
            shared_state.set_video_source(src_type, path, cam_idx)

    def on_raw_frame(self, frame):
        self.input_monitor.setPixmap(self._cv_to_pixmap(frame, 450, 335))

    def on_processed_frame(self, frame):
        self.output_monitor.setPixmap(self._cv_to_pixmap(frame, 450, 335))
        if self.floating_window.isVisible():
            self.floating_window.update_frame(frame)

    def _cv_to_pixmap(self, img, w, h):
        ih, iw, ch = img.shape
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return QPixmap.fromImage(QImage(rgb.data, iw, ih, ch * iw, QImage.Format.Format_RGB888)).scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def on_face_count_update(self, c):
        self.status_lbl.setText(f"Detected Faces: {c} | 3D Mocap: Active")

    def on_audio_level_update(self, lvl):
        self.vu.setValue(min(100, int((lvl / 1200.0) * 100)))

    def toggle_obs(self):
        if self.floating_window.isVisible():
            self.floating_window.hide()
            self.obs_btn.setText("🚀 Launch Floating OBS Window")
        else:
            self.floating_window.show()
            self.obs_btn.setText("⏹️ Close Floating OBS Window")

    def start_download(self):
        self.dl_btn.setEnabled(False)
        self.dl_worker = DownloadWorker()
        self.dl_worker.progress_signal.connect(lambda msg, p: self.dl_prog_lbl.setText(msg))
        self.dl_worker.finished_signal.connect(self.on_download_complete)
        self.dl_worker.start()

    def on_download_complete(self):
        self.dl_btn.setEnabled(True)
        self.dl_prog_lbl.setText("✓ All downloads complete!")
        for name, (path, _) in MODELS_INFO.items():
            if os.path.exists(path):
                self.model_status_labels[name].setText(f"• {name}: ✓ Installed")
                self.model_status_labels[name].setStyleSheet("color: #00B37E; font-weight: bold; font-size: 13px;")

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
