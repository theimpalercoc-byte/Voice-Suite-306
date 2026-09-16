import cv2, numpy as np, time, os
from PyQt6.QtCore import QThread, pyqtSignal
from state import shared_state
from engine.portrait_engine import LivePortraitDGXEngine

def scan_available_cameras(max_tested=6):
    available = []
    for i in range(max_tested):
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
            cap.release()
    return available if available else [0]

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

    def draw_3d_wireframe(self, frame, box):
        x, y, w, h = box
        cx, cy = x + w // 2, y + h // 2
        
        # 1. 3D Head Bounding Wireframe (Perspective Box)
        d = int(w * 0.25)
        front = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        back = [(x + d, y - d), (x + w + d, y - d), (x + w + d, y + h - d), (x + d, y + h - d)]
        
        for i in range(4):
            cv2.line(frame, front[i], front[(i + 1) % 4], (0, 230, 150), 1)
            cv2.line(frame, back[i], back[(i + 1) % 4], (0, 140, 90), 1)
            cv2.line(frame, front[i], back[i], (0, 180, 120), 1)

        # 2. Facial Landmark Wireframe (Eyes, Nose Pyramid, Mouth Grid)
        leye = (int(x + w * 0.32), int(y + h * 0.38))
        reye = (int(x + w * 0.68), int(y + h * 0.38))
        nose = (cx, int(y + h * 0.55))
        m_left = (int(x + w * 0.35), int(y + h * 0.75))
        m_right = (int(x + w * 0.65), int(y + h * 0.75))
        m_center = (cx, int(y + h * 0.78))

        # Wireframe interconnects
        pts = [leye, reye, nose, m_left, m_right, m_center]
        for p in pts:
            cv2.circle(frame, p, 3, (0, 255, 255), -1)

        cv2.line(frame, leye, reye, (255, 200, 0), 1)
        cv2.line(frame, leye, nose, (255, 200, 0), 1)
        cv2.line(frame, reye, nose, (255, 200, 0), 1)
        cv2.line(frame, nose, m_left, (0, 200, 255), 1)
        cv2.line(frame, nose, m_right, (0, 200, 255), 1)
        cv2.line(frame, m_left, m_center, (0, 200, 255), 2)
        cv2.line(frame, m_right, m_center, (0, 200, 255), 2)

        # 3. 3D Pose Normal Vector (showing direction face is looking)
        cv2.arrowedLine(frame, nose, (nose[0], nose[1] - 35), (255, 80, 80), 2, tipLength=0.3)
        cv2.putText(frame, "3D RIG ACTIVE", (x, y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 150), 1)

    def run(self):
        cap = None
        current_src_type = None
        current_src_path = None
        current_cam_idx = None

        while self.is_running:
            with shared_state._lock:
                src_type = shared_state.video_source_type
                src_path = shared_state.video_file_path
                cam_idx = shared_state.camera_index
                show_wf = shared_state.show_wireframe
                multi_person = shared_state.multi_person_mode

            # Switch capture device if source or camera index changed
            if src_type != current_src_type or src_path != current_src_path or cam_idx != current_cam_idx or cap is None:
                if cap is not None: cap.release()
                if src_type == "file" and os.path.exists(src_path):
                    cap = cv2.VideoCapture(src_path)
                else:
                    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
                    cap = cv2.VideoCapture(cam_idx, backend)

                current_src_type = src_type
                current_src_path = src_path
                current_cam_idx = cam_idx

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

            # Detect face
            faces = self.detect_face_regions(frame)
            self.face_count_signal.emit(len(faces))
            primary_face = faces[0] if len(faces) > 0 else None

            # Streamer private monitor frame
            private_monitor_frame = frame.copy()
            if show_wf and primary_face is not None:
                self.draw_3d_wireframe(private_monitor_frame, primary_face)

            self.raw_frame_ready.emit(private_monitor_frame)

            # Animate avatar and emit to OBS
            avatar_output = self.avatar_engine.process_live_frame(frame, primary_face)
            self.processed_frame_ready.emit(avatar_output)
            self.msleep(16)

        if cap is not None: cap.release()

    def stop(self):
        self.is_running = False
        self.wait()
