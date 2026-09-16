import cv2, numpy as np, time, os
from PyQt6.QtCore import QThread, pyqtSignal
from state import shared_state
from engine.portrait_engine import LivePortraitDGXEngine

class VideoPipelineThread(QThread):
    raw_frame_ready = pyqtSignal(np.ndarray)
    processed_frame_ready = pyqtSignal(np.ndarray)
    face_count_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.avatar_engine = LivePortraitDGXEngine()

    def detect_face_regions(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if 40 < w < 450 and 40 < h < 450:
                boxes.append((x, y, w, h))
        if len(boxes) > 0:
            return sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
        h, w = frame.shape[:2]
        return [((w - int(w * 0.35)) // 2, (h - int(h * 0.45)) // 2, int(w * 0.35), int(h * 0.45))]

    def run(self):
        cap = None
        current_src_type = None
        current_src_path = None

        while self.is_running:
            with shared_state._lock:
                src_type = shared_state.video_source_type
                src_path = shared_state.video_file_path
                multi_person = shared_state.multi_person_mode

            if src_type != current_src_type or src_path != current_src_path or cap is None:
                if cap is not None: cap.release()
                cap = cv2.VideoCapture(src_path if (src_type == "file" and os.path.exists(src_path)) else 0)
                current_src_type, current_src_path = src_type, src_path

            ret, frame = (False, None)
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret and current_src_type == "file":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()

            if not ret or frame is None:
                frame = np.full((480, 640, 3), 30, dtype=np.uint8)
                time.sleep(0.03)
            elif current_src_type == "camera":
                frame = cv2.flip(frame, 1)

            # 1. Private monitor displays raw input
            self.raw_frame_ready.emit(frame.copy())

            # 2. Tracking
            faces = self.detect_face_regions(frame)
            self.face_count_signal.emit(len(faces))
            primary_face = faces[0] if len(faces) > 0 else None

            # 3. Animate avatar via puppetry engine
            avatar_output = self.avatar_engine.process_live_frame(frame, primary_face)

            # 4. Emit to Cam Output monitor & Floating OBS Window
            self.processed_frame_ready.emit(avatar_output)
            self.msleep(16)

        if cap is not None: cap.release()

    def stop(self):
        self.is_running = False
        self.wait()
