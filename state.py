import threading
from dataclasses import dataclass, field
from typing import Dict, Tuple

@dataclass
class AppState:
    # Video & Camera
    video_source_type: str = "camera"
    video_file_path: str = ""
    camera_index: int = 0
    camera_resolution: str = "640x480"
    show_wireframe: bool = True
    multi_person_mode: bool = False
    active_target_face: int = 0
    audio_video_delay_ms: int = 50

    # Audio & Voice Suite
    audio_source_type: str = "mic"
    audio_file_path: str = ""
    audio_input_device: int = 0
    audio_output_device: int = 0
    is_audio_running: bool = False
    pitch_semitones: int = 0
    reverb_intensity: int = 0
    echo_delay: int = 0
    noise_gate_threshold: int = 20
    selected_voice_model: str = "None (DSP Passthrough)"

    # Rigging Anchors
    calibration_pins: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "Left Eye": (180.0, 200.0),
        "Right Eye": (320.0, 200.0),
        "Nose Tip": (250.0, 270.0),
        "Mouth Left": (190.0, 360.0),
        "Mouth Right": (310.0, 360.0),
    })

    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set_video_source(self, src: str, path: str = "", cam_idx: int = 0):
        with self._lock:
            self.video_source_type = src
            self.video_file_path = path
            self.camera_index = cam_idx

    def set_camera_index(self, idx: int):
        with self._lock:
            self.camera_index = idx

    def toggle_wireframe(self, val: bool):
        with self._lock:
            self.show_wireframe = val

    def toggle_multi_person(self, val: bool):
        with self._lock:
            self.multi_person_mode = val

    def set_audio_source(self, src: str, path: str = ""):
        with self._lock:
            self.audio_source_type = src
            self.audio_file_path = path

    def update_fx(self, pitch: int, reverb: int, echo: int, gate: int):
        with self._lock:
            self.pitch_semitones = pitch
            self.reverb_intensity = reverb
            self.echo_delay = echo
            self.noise_gate_threshold = gate

    def update_pins(self, pin_dict: Dict[str, Tuple[float, float]]):
        with self._lock:
            self.calibration_pins = pin_dict

    def get_pins(self) -> Dict[str, Tuple[float, float]]:
        with self._lock:
            return self.calibration_pins.copy()

shared_state = AppState()
