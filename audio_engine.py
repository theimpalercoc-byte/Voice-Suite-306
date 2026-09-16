import wave
import numpy as np
import time
import os
from PyQt6.QtCore import QThread, pyqtSignal
from state import shared_state

class AudioPipelineThread(QThread):
    audio_level_signal = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.is_running = True

    def run(self):
        while self.is_running:
            with shared_state._lock:
                src_type = shared_state.audio_source_type
                src_path = shared_state.audio_file_path
                pitch = shared_state.pitch_semitones

            # File Playback Mode
            if src_type == "file" and os.path.exists(src_path):
                try:
                    wf = wave.open(src_path, 'rb')
                    chunk_size = 1024
                    while self.is_running and shared_state.audio_source_type == "file":
                        data = wf.readframes(chunk_size)
                        if len(data) == 0:
                            wf.rewind()  # Loop audio file
                            continue
                        
                        audio_data = np.frombuffer(data, dtype=np.int16)
                        
                        # Apply Pitch Modification DSP
                        if pitch != 0:
                            factor = 2 ** (pitch / 12.0)
                            indices = np.round(np.arange(0, len(audio_data), factor))
                            indices = indices[indices < len(audio_data)].astype(int)
                            audio_data = audio_data[indices]

                        # Calculate volume level for UI meter
                        volume = float(np.abs(audio_data).mean()) if len(audio_data) > 0 else 0.0
                        self.audio_level_signal.emit(volume)
                        time.sleep(0.02)
                    wf.close()
                except Exception as e:
                    time.sleep(0.1)
            else:
                # Simulated silence/idle tone when no mic or file active
                self.audio_level_signal.emit(0.0)
                time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.wait()
