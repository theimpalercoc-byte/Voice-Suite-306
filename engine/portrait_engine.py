import os, cv2, numpy as np
from state import shared_state

try:
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None
    HAS_TORCH = False

class LivePortraitDGXEngine:
    def __init__(self, model_dir="./weights"):
        self.model_dir = model_dir
        self.device = "cuda" if (HAS_TORCH and torch.cuda.is_available()) else "cpu"
        self.has_cuda = (self.device == "cuda")
        self.source_avatar_img = None
        self.is_rigged = False

        default_path = "avatars/default_avatar.png"
        if os.path.exists(default_path):
            self.prepare_avatar_source(cv2.imread(default_path), shared_state.get_pins())

    def prepare_avatar_source(self, img_array, manual_pins):
        if img_array is None: return False
        self.source_avatar_img = cv2.resize(img_array, (500, 500))
        self.is_rigged = True
        return True

    def process_live_frame(self, driving_frame, face_box=None):
        if not self.is_rigged or self.source_avatar_img is None:
            return driving_frame

        h, w = driving_frame.shape[:2]
        if face_box is not None and len(face_box) == 4:
            fx, fy, fw, fh = face_box
            dx = ((fx + fw // 2) - (w // 2)) * 0.4
            dy = ((fy + fh // 2) - (h // 2)) * 0.4
            scale = np.clip(fw / (w * 0.35), 0.85, 1.15)
        else:
            dx, dy, scale = 0.0, 0.0, 1.0

        M = cv2.getRotationMatrix2D((250, 250), 0, scale)
        M[0, 2] += dx
        M[1, 2] += dy

        warped = cv2.warpAffine(self.source_avatar_img, M, (500, 500), borderMode=cv2.BORDER_CONSTANT, borderValue=(18, 18, 20))
        cv2.putText(warped, "AI AVATAR: LIVE", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 150), 2)
        return warped
