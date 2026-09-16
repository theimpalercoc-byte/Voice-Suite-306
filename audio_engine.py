import os, time, wave, numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from state import shared_state

class AudioPipelineThread(QThread):
    audio_level_signal = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.echo_buffer = np.zeros(44100, dtype=np.float32)
        self.echo_idx = 0

    def apply_dsp_effects(self, audio_data: np.ndarray) -> np.ndarray:
        pitch = shared_state.pitch_semitones
        reverb = shared_state.reverb_intensity / 100.0
        echo = shared_state.echo_delay / 100.0
        gate = shared_state.noise_gate_threshold

        float_audio = audio_data.astype(np.float32)

        # 1. Noise Gate
        rms = np.sqrt(np.mean(float_audio**2)) if len(float_audio) > 0 else 0
        if rms < (gate * 50):
            return np.zeros_like(audio_data)

        # 2. Pitch Shift (Interpolation DSP)
        if pitch != 0:
            factor = 2 ** (pitch / 12.0)
            indices = np.round(np.arange(0, len(float_audio), factor))
            indices = indices[indices < len(float_audio)].astype(int)
            float_audio = float_audio[indices]
            if len(float_audio) < len(audio_data):
                float_audio = np.pad(float_audio, (0, len(audio_data) - len(float_audio)), "constant")
            float_audio = float_audio[:len(audio_data)]

        # 3. Echo & Reverb Delay Line
        if echo > 0 or reverb > 0:
            delay_samples = int(44100 * (0.05 + echo * 0.35))
            for i in range(len(float_audio)):
                buf_pos = (self.echo_idx - delay_samples) % len(self.echo_buffer)
                echo_val = self.echo_buffer[buf_pos] * (echo * 0.6 + reverb * 0.3)
                self.echo_buffer[self.echo_idx] = float_audio[i] + echo_val * 0.4
                float_audio[i] += echo_val
                self.echo_idx = (self.echo_idx + 1) % len(self.echo_buffer)

        return np.clip(float_audio, -32768, 32767).astype(np.int16)

    def run(self):
        chunk_size = 1024
        while self.is_running:
            with shared_state._lock:
                src_type = shared_state.audio_source_type
                src_path = shared_state.audio_file_path

            if src_type == "file" and os.path.exists(src_path):
                try:
                    wf = wave.open(src_path, "rb")
                    while self.is_running and shared_state.audio_source_type == "file":
                        data = wf.readframes(chunk_size)
                        if len(data) == 0:
                            wf.rewind()
                            continue
                        raw = np.frombuffer(data, dtype=np.int16)
                        processed = self.apply_dsp_effects(raw)
                        vol = float(np.abs(processed).mean()) if len(processed) > 0 else 0.0
                        self.audio_level_signal.emit(vol)
                        time.sleep(0.02)
                    wf.close()
                except Exception:
                    time.sleep(0.1)
            else:
                self.audio_level_signal.emit(0.0)
                time.sleep(0.05)

    def stop(self):
        self.is_running = False
        self.wait()
