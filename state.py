import threading
from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass
class AppState:
    # --- Video & Camera Settings ---
    video_source_type: str = "camera"   # "camera" or "file"
    video_file_path: str = ""
    camera_index: int = 0
    show_wireframe: bool = True         # 3D tracking wireframe overlay
    multi_person_mode: bool = False
    active_target_face: int = 0
    audio_video_delay_ms: int = 45

    # --- Audio Settings ---
    audio_source_type: str = "mic"
    audio_file_path: str = ""
    is_audio_running: bool = False
    pitch_semitones: int = 0
    reverb_intensity: int = 0
    noise_gate_threshold: int = 30
    selected_voice_model: str = ""

    # --- Rigging Landmarks ---
    calibration_pins: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "Left Eye": (180.0, 200.0),
        "Right Eye": (320.0, 200.0),
        "Nose Tip": (250.0, 270.0),
        "Mouth Left": (190.0, 360.0),
        "Mouth Right": (310.0, 360.0),
    })

    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set_video_source(self, source_type: str, path: str = "", cam_idx: int = 0):
        with self._lock:
            self.video_source_type = source_type
            self.video_file_path = path
            self.camera_index = cam_idx

    def set_camera_index(self, idx: int):
        with self._lock:
            self.camera_index = idx

    def toggle_wireframe(self, enabled: bool):
        with self._lock:
            self.show_wireframe = enabled

    def set_audio_source(self, source_type: str, path: str = ""):
        with self._lock:
            self.audio_source_type = source_type
            self.audio_file_path = path

    def toggle_multi_person(self, enabled: bool):
        with self._lock:
            self.multi_person_mode = enabled

    def update_pitch(self, val: int):
        with self._lock:
            self.pitch_semitones = val

    def get_pitch(self) -> int:
        with self._lock:
            return self.pitch_semitones

    def update_pins(self, pin_dict: Dict[str, Tuple[float, float]]):
        with self._lock:
            self.calibration_pins = pin_dict

    def get_pins(self) -> Dict[str, Tuple[float, float]]:
        with self._lock:
            return self.calibration_pins.copy()

shared_state = AppState()
