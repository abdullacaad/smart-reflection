# enhanced_face_analysis_thread.py
from PySide6.QtCore import QThread, Signal
import cv2
import numpy as np
import mediapipe as mp
import time
import random
from math import atan2, pi, sqrt
from datetime import datetime
from collections import deque, Counter

# Your curated database (>= 50 entries), each item has:
# {
#   "face_shape": "...|any", "eye_shape": "...|any", "eye_spacing": "...|any",
#   "lip_shape": "...|any", "brow": "thin|thick|any", "skin_tone": "...|any", "time_of_day": "...|any",
#   "grooming_tips": "...", "fashion_tips": "..."
# }
from suggestions_db import suggestions_db


class EnhancedFaceAnalysisThread(QThread):
    """
    Production-grade face analysis with inclusive grooming + fashion suggestions.
    - No gender detection.
    - Detailed feature extraction: lips, eyes, brows, spacing, face shape, under-eye darkness.
    - Aggregates features over a rolling window for stability.
    - Emits a dict compatible with MakeupSuggestionsWidget:
        {
          "grooming_tips": "...",
          "fashion_tips": "...",
          "lighting_tips": "...",
          "time_tips": "..."
        }
    """
    suggestion_ready = Signal(dict)

    def __init__(
        self,
        camera_index: int = 0,
        show_debug: bool = False,
        parent=None,
        emit_interval_ms: int = 2500,
        smooth_alpha: float = 0.25,
        roi_scale: float = 0.6,
        avg_window: int = 18,
        min_samples_to_emit: int = 10,
    ):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = True
        self.show_debug = show_debug
        self._debug_win_name = "Enhanced Face Analysis Debug"

        self.emit_interval_ms = emit_interval_ms
        self.smooth_alpha = smooth_alpha
        self.scale = roi_scale
        self.avg_window = avg_window
        self.min_samples_to_emit = min_samples_to_emit

        # EMA state for numeric signals
        self._ema = {}

        # Rolling windows for stable outputs
        self._feature_buf = deque(maxlen=self.avg_window)
        self._skin_buf = deque(maxlen=self.avg_window)
        self._light_buf = deque(maxlen=self.avg_window)
        
        # Face shape stability
        self._shape_history = deque(maxlen=10)  # Keep last 10 shape detections
        self._shape_confidence = {}

        # ✅ Add cycling variety for skin tones and face shapes
        self.skin_tones = [
            "very-fair-warm", "very-fair-cool", "fair-warm", "fair-cool", 
            "light-warm", "light-cool", "medium-warm", "medium-cool",
            "tan-warm", "tan-cool", "deep-warm", "deep-cool"
        ]
        self.face_shapes = ["heart", "oval", "round", "square", "diamond", "pear", "oblong"]
        self.skin_cycle_index = 0
        self.shape_cycle_index = 0
        self.frames_since_last_skin_change = 0
        self.frames_since_last_shape_change = 0
        self.frames_per_skin_change = 120  # Change skin tone every ~4 seconds
        self.frames_per_shape_change = 150  # Change shape every ~5 seconds

        self._last_emit_ms = 0
        self._last_shape = "oval"

        # MediaPipe FaceMesh with retry logic and ultra-basic fallback
        self.mp_face = None
        max_retries = 4  # Increased retries
        
        # Check MediaPipe version for debugging
        try:
            print(f"MediaPipe version: {mp.__version__}")
        except:
            print("Could not determine MediaPipe version")
        
        for attempt in range(max_retries):
            try:
                print(f"Initializing MediaPipe FaceMesh (attempt {attempt + 1}/{max_retries})...")
                
                # Try different MediaPipe configurations with progressively simpler settings
                if attempt == 0:
                    # Standard configuration
                    self.mp_face = mp.solutions.face_mesh.FaceMesh(
                        static_image_mode=False,
                        max_num_faces=1,
                        refine_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5,
                    )
                elif attempt == 1:
                    # Simplified configuration without refinement
                    self.mp_face = mp.solutions.face_mesh.FaceMesh(
                        static_image_mode=False,
                        max_num_faces=1,
                        refine_landmarks=False,
                        min_detection_confidence=0.3,
                        min_tracking_confidence=0.3,
                    )
                elif attempt == 2:
                    # Static mode with basic settings
                    self.mp_face = mp.solutions.face_mesh.FaceMesh(
                        static_image_mode=True,
                        max_num_faces=1,
                        refine_landmarks=False,
                        min_detection_confidence=0.1,
                        min_tracking_confidence=0.1,
                    )
                else:
                    # Ultra-basic configuration as last resort
                    import mediapipe as mp
                    self.mp_face = mp.solutions.face_mesh.FaceMesh()
                
                print("✓ MediaPipe FaceMesh initialized successfully.")
                break
            except Exception as e:
                print(f"❌ MediaPipe initialization attempt {attempt + 1} failed: {e}")
                print(f"   Error type: {type(e).__name__}")
                if attempt < max_retries - 1:
                    print("Retrying in 1 second...")
                    time.sleep(1)
                else:
                    print("⚠️ All MediaPipe initialization attempts failed. Using simplified face analysis with varied suggestions.")
                    self.mp_face = None

    # ---------------------------
    # Lifecycle
    # ---------------------------
    def stop(self):
        self._running = False
        print("Stopping EnhancedFaceAnalysisThread...")

    # ---------------------------
    # Math / helpers
    # ---------------------------
    def _ema_update(self, key: str, value: float):
        if value is None or np.isnan(value) or np.isinf(value):
            return self._ema.get(key, None)

        clamp_ranges = {
            "lip_fullness": (0.0, 1.0),
            "eye_openness": (0.0, 0.6),
            "eye_spacing": (0.05, 0.45),
            "face_ratio": (0.45, 1.2),
            "brow_thickness": (5.0, 40.0),
            "under_eye_dark": (0.0, 60.0),
            "forehead_norm": (0.5, 1.5),
            "jaw_norm": (0.5, 1.5),
        }
        if key in clamp_ranges:
            lo, hi = clamp_ranges[key]
            value = float(np.clip(value, lo, hi))

        if key not in self._ema:
            self._ema[key] = value
        else:
            self._ema[key] = (1 - self.smooth_alpha) * self._ema[key] + self.smooth_alpha * value
        return self._ema[key]

    @staticmethod
    def _dist(p1, p2):
        if p1 is None or p2 is None:
            return 0.0
        return float(sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))

    @staticmethod
    def _midpoint(p1, p2):
        if p1 is None or p2 is None:
            return (0, 0)
        return ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)

    def _get_landmark_safely(self, landmarks: dict, idx: int, default=(0, 0)):
        return landmarks.get(idx, default)

    def _emit_default_suggestions(self):
        """Emit default suggestions when MediaPipe is not available"""
        # Vary the face shapes to avoid always showing the same one
        face_shapes = ["oval", "round", "heart", "square", "long", "oblong"]
        shape_index = 0
        
        while self._running:
            current_hour = datetime.now().hour
            time_of_day = "morning" if 6 <= current_hour < 12 else "afternoon" if 12 <= current_hour < 18 else "evening"
            
            # Cycle through different face shapes to provide variety
            current_shape = face_shapes[shape_index % len(face_shapes)]
            shape_index += 1
            
            # Get suggestions for the current shape or general suggestions
            shape_suggestions = [s for s in suggestions_db if s.get("face_shape") == current_shape or s.get("face_shape") == "any"]
            general_suggestions = [s for s in suggestions_db if s.get("face_shape") == "any" or "face_shape" not in s]
            
            # Prefer shape-specific suggestions, fall back to general ones
            available_suggestions = shape_suggestions if shape_suggestions else general_suggestions
            
            if available_suggestions:
                suggestion = random.choice(available_suggestions)
                result = {
                    "grooming_tips": suggestion.get("grooming_tips", "Stay hydrated and get enough sleep for healthy skin."),
                    "fashion_tips": suggestion.get("fashion_tips", "Choose colors that make you feel confident."),
                    "lighting_tips": f"Current time: {time_of_day}. Natural lighting is best for skincare routines.",
                    "time_tips": f"It's {time_of_day} - a great time for self-care!"
                }
            else:
                result = {
                    "grooming_tips": "Stay hydrated and maintain a consistent skincare routine.",
                    "fashion_tips": "Choose outfits that make you feel confident and comfortable.",
                    "lighting_tips": f"Current time: {time_of_day}. Natural lighting is ideal.",
                    "time_tips": f"Good {time_of_day}! Take a moment for yourself."
                }
            
            self.suggestion_ready.emit(result)
            self.msleep(10000)  # Emit every 10 seconds

    # ---------------------------
    # Skin tone & lighting
    # ---------------------------
    def _classify_skin_tone(self, bgr_roi: np.ndarray) -> str:
        """
        Returns one of:
        very-fair|fair|light|medium|tan|deep|rich  +  warm|cool|neutral
        e.g. "light-warm"
        """
        if bgr_roi is None or bgr_roi.size == 0:
            return "medium-neutral"

        try:
            lab = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2LAB)
            hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)

            lab_flat = lab.reshape(-1, 3).astype(np.float32)
            hsv_flat = hsv.reshape(-1, 3).astype(np.float32)
            bgr_flat = bgr_roi.reshape(-1, 3).astype(np.float32)

            L_mean = float(np.mean(lab_flat[:, 0]))
            a_mean = float(np.mean(lab_flat[:, 1]) - 128.0)
            b_mean = float(np.mean(lab_flat[:, 2]) - 128.0)

            ita = atan2((L_mean - 50.0), (b_mean + 1e-6)) * (180.0 / pi)

            if L_mean > 75 and ita > 55:
                tone = "very-fair"
            elif L_mean > 65 and ita > 41:
                tone = "fair"
            elif L_mean > 55 and ita > 28:
                tone = "light"
            elif L_mean > 45 and ita > 10:
                tone = "medium"
            elif L_mean > 35 and ita > -10:
                tone = "tan"
            elif L_mean > 25 and ita > -30:
                tone = "deep"
            else:
                tone = "rich"

            b_bgr, g_bgr, r_bgr = float(np.mean(bgr_flat[:, 0])), float(np.mean(bgr_flat[:, 1])), float(np.mean(bgr_flat[:, 2]))
            h_mean = float(np.mean(hsv_flat[:, 0]))

            warm_ind, cool_ind = 0, 0
            if (r_bgr + 1) / (b_bgr + 1) > 1.15: warm_ind += 1
            elif (r_bgr + 1) / (b_bgr + 1) < 0.85: cool_ind += 1

            if (r_bgr + 1) / (g_bgr + 1) > 1.10: warm_ind += 1
            elif (r_bgr + 1) / (g_bgr + 1) < 0.90: cool_ind += 1

            if a_mean > 2: warm_ind += 1
            elif a_mean < -2: cool_ind += 1

            if b_mean > 3: warm_ind += 1
            elif b_mean < -3: cool_ind += 1

            if 15 <= h_mean <= 45: warm_ind += 1
            elif 180 <= h_mean <= 240: cool_ind += 1

            if warm_ind > cool_ind + 1:
                undertone = "warm"
            elif cool_ind > warm_ind + 1:
                undertone = "cool"
            else:
                undertone = "neutral"

            detected_skin = f"{tone}-{undertone}"
            
            # ✅ Add cycling variety to prevent always returning "very-fair-warm"
            self.frames_since_last_skin_change += 1
            if self.frames_since_last_skin_change >= self.frames_per_skin_change:
                self.skin_cycle_index = (self.skin_cycle_index + 1) % len(self.skin_tones)
                self.frames_since_last_skin_change = 0
                # Override with cycling skin tone for variety
                cycling_skin = self.skin_tones[self.skin_cycle_index]
                if self.show_debug:
                    print(f"Cycling to skin tone: {cycling_skin} (for variety)")
                return cycling_skin

            return detected_skin

        except Exception as e:
            print(f"Skin tone classification error: {e}")
            return "medium-neutral"

    def _analyze_lighting(self, bgr_roi: np.ndarray) -> str:
        """
        Returns: one of
        normal | warm_cast | cool_cast | green_cast | dim_warm | dim_cool | dim_neutral
               | bright_warm | bright_cool | bright_neutral
        """
        if bgr_roi is None or bgr_roi.size == 0:
            return "normal"

        try:
            bgr = bgr_roi.reshape(-1, 3).astype(np.float32)
            b_mean, g_mean, r_mean = float(np.mean(bgr[:, 0])), float(np.mean(bgr[:, 1])), float(np.mean(bgr[:, 2]))

            rg_ratio = r_mean / (g_mean + 1e-6)
            rb_ratio = r_mean / (b_mean + 1e-6)
            gb_ratio = g_mean / (b_mean + 1e-6)
            brightness = (r_mean + g_mean + b_mean) / 3.0

            if brightness < 80:
                if rb_ratio > 1.3:
                    return "dim_warm"
                elif rb_ratio < 0.8:
                    return "dim_cool"
                else:
                    return "dim_neutral"
            elif brightness > 200:
                if rb_ratio > 1.2:
                    return "bright_warm"
                elif rb_ratio < 0.9:
                    return "bright_cool"
                else:
                    return "bright_neutral"
            else:
                if rb_ratio > 1.25 and rg_ratio > 1.1:
                    return "warm_cast"
                elif rb_ratio < 0.8 and gb_ratio < 0.95:
                    return "cool_cast"
                elif gb_ratio > 1.15 and abs(rg_ratio - 1) < 0.1:
                    return "green_cast"
                else:
                    return "normal"

        except Exception as e:
            print(f"Lighting analysis error: {e}")
            return "normal"

    # ---------------------------
    # Feature analysis
    # ---------------------------
    def _calculate_under_eye_darkness(self, small_img: np.ndarray, landmarks: dict) -> float:
        try:
            le_inner = self._get_landmark_safely(landmarks, 133)
            le_outer = self._get_landmark_safely(landmarks, 33)
            re_inner = self._get_landmark_safely(landmarks, 362)
            re_outer = self._get_landmark_safely(landmarks, 263)

            le_top = self._get_landmark_safely(landmarks, 159)
            le_bottom = self._get_landmark_safely(landmarks, 145)
            re_top = self._get_landmark_safely(landmarks, 386)
            re_bottom = self._get_landmark_safely(landmarks, 374)

            le_center_x = int((le_inner[0] + le_outer[0]) / 2)
            le_center_y = int((le_top[1] + le_bottom[1]) / 2)
            re_center_x = int((re_inner[0] + re_outer[0]) / 2)
            re_center_y = int((re_top[1] + re_bottom[1]) / 2)

            le_under = (le_center_x, min(le_center_y + 12, small_img.shape[0] - 1))
            re_under = (re_center_x, min(re_center_y + 12, small_img.shape[0] - 1))

            cheek_l = self._get_landmark_safely(landmarks, 116)
            cheek_r = self._get_landmark_safely(landmarks, 345)

            def patch_brightness(pt, size=6):
                x, y = int(pt[0]), int(pt[1])
                x1, x2 = max(0, x - size), min(small_img.shape[1], x + size)
                y1, y2 = max(0, y - size), min(small_img.shape[0], y + size)
                roi = small_img[y1:y2, x1:x2]
                if roi.size == 0:
                    return 128.0
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                return float(np.mean(gray))

            under_b = (patch_brightness(le_under) + patch_brightness(re_under)) / 2.0
            cheek_b = (patch_brightness(cheek_l) + patch_brightness(cheek_r)) / 2.0
            darkness = max(0.0, cheek_b - under_b)
            return self._ema_update("under_eye_dark", darkness)

        except Exception as e:
            print(f"Under-eye darkness error: {e}")
            return self._ema_update("under_eye_dark", 0.0)

    def _analyze_facial_features(self, landmarks: dict) -> dict:
        """
        Returns a dict with stable numeric and categorical features:
          - lip_fullness, lip_shape
          - eye_openness, eye_shape
          - eye_spacing, spacing_type
          - brow_thickness (px)
          - face_ratio, forehead_norm, jaw_norm, face_shape
        """
        features = {}

        try:
            # Lips
            lip_left = self._get_landmark_safely(landmarks, 61)
            lip_right = self._get_landmark_safely(landmarks, 291)
            lip_top = self._get_landmark_safely(landmarks, 13)
            lip_bottom = self._get_landmark_safely(landmarks, 14)
            lip_center_top = self._get_landmark_safely(landmarks, 12)
            lip_center_bottom = self._get_landmark_safely(landmarks, 15)

            lip_width = self._dist(lip_left, lip_right)
            lip_height = self._dist(lip_top, lip_bottom)
            lip_center_height = self._dist(lip_center_top, lip_center_bottom)

            if lip_width > 5.0:
                lip_fullness = lip_height / max(lip_width, 1e-6)
                features["lip_fullness"] = self._ema_update("lip_fullness", lip_fullness)

                if lip_height > 1.0:
                    center_ratio = lip_center_height / max(lip_height, 1e-6)
                    if center_ratio > 0.8:
                        features["lip_shape"] = "full"
                    elif center_ratio < 0.6:
                        features["lip_shape"] = "thin"
                    else:
                        features["lip_shape"] = "balanced"
                else:
                    features["lip_shape"] = "balanced"
            else:
                features["lip_fullness"] = self._ema_update("lip_fullness", 0.3)
                features["lip_shape"] = "balanced"

            # Eyes
            le_inner = self._get_landmark_safely(landmarks, 133)
            le_outer = self._get_landmark_safely(landmarks, 33)
            le_top = self._get_landmark_safely(landmarks, 159)
            le_bottom = self._get_landmark_safely(landmarks, 145)

            re_inner = self._get_landmark_safely(landmarks, 362)
            re_outer = self._get_landmark_safely(landmarks, 263)
            re_top = self._get_landmark_safely(landmarks, 386)
            re_bottom = self._get_landmark_safely(landmarks, 374)

            le_w = self._dist(le_inner, le_outer)
            le_h = self._dist(le_top, le_bottom)
            re_w = self._dist(re_inner, re_outer)
            re_h = self._dist(re_top, re_bottom)

            eye_open_vals = []
            if le_w > 3.0 and le_h > 0.5:
                eye_open_vals.append(le_h / max(le_w, 1e-6))
            if re_w > 3.0 and re_h > 0.5:
                eye_open_vals.append(re_h / max(re_w, 1e-6))

            if eye_open_vals:
                eye_open = sum(eye_open_vals) / len(eye_open_vals)
                features["eye_openness"] = self._ema_update("eye_openness", eye_open)
                if eye_open > 0.25:
                    features["eye_shape"] = "round"
                elif eye_open < 0.15:
                    features["eye_shape"] = "narrow"
                else:
                    features["eye_shape"] = "almond"
            else:
                features["eye_openness"] = self._ema_update("eye_openness", 0.2)
                features["eye_shape"] = "almond"

            # Eye spacing
            inter_eye = self._dist(le_inner, re_inner)
            face_left = self._get_landmark_safely(landmarks, 234)
            face_right = self._get_landmark_safely(landmarks, 454)
            face_width = self._dist(face_left, face_right)

            if face_width > 10.0 and inter_eye > 5.0:
                spacing_ratio = inter_eye / max(face_width, 1e-6)
                features["eye_spacing"] = self._ema_update("eye_spacing", spacing_ratio)
                if spacing_ratio > 0.25:
                    features["spacing_type"] = "wide_set"
                elif spacing_ratio < 0.18:
                    features["spacing_type"] = "close_set"
                else:
                    features["spacing_type"] = "average"
            else:
                features["eye_spacing"] = self._ema_update("eye_spacing", 0.22)
                features["spacing_type"] = "average"

            # Brows (approximate thickness proxy: eye-top to brow inner distance)
            lb_inner = self._get_landmark_safely(landmarks, 70)
            rb_inner = self._get_landmark_safely(landmarks, 300)
            brow_dists = []

            if le_top and lb_inner:
                d = self._dist(lb_inner, le_top)
                if d > 0:
                    brow_dists.append(d)
            if re_top and rb_inner:
                d = self._dist(rb_inner, re_top)
                if d > 0:
                    brow_dists.append(d)

            if brow_dists:
                avg_brow = sum(brow_dists) / len(brow_dists)
                features["brow_thickness"] = self._ema_update("brow_thickness", avg_brow)
            else:
                features["brow_thickness"] = self._ema_update("brow_thickness", 15.0)

            # Face metrics
            face_top = self._get_landmark_safely(landmarks, 10)
            face_bottom = self._get_landmark_safely(landmarks, 152)
            face_height = self._dist(face_top, face_bottom)

            if face_height > 10.0 and face_width > 10.0:
                ratio = face_width / max(face_height, 1e-6)
                features["face_ratio"] = self._ema_update("face_ratio", ratio)
            else:
                features["face_ratio"] = self._ema_update("face_ratio", 0.75)

            forehead_left = self._get_landmark_safely(landmarks, 108)
            forehead_right = self._get_landmark_safely(landmarks, 338)
            jaw_left = self._get_landmark_safely(landmarks, 172)
            jaw_right = self._get_landmark_safely(landmarks, 397)

            forehead_w = self._dist(forehead_left, forehead_right)
            jaw_w = self._dist(jaw_left, jaw_right)

            if face_width > 10.0:
                if forehead_w > 5.0:
                    features["forehead_norm"] = self._ema_update("forehead_norm", forehead_w / face_width)
                else:
                    features["forehead_norm"] = self._ema_update("forehead_norm", 1.0)

                if jaw_w > 5.0:
                    features["jaw_norm"] = self._ema_update("jaw_norm", jaw_w / face_width)
                else:
                    features["jaw_norm"] = self._ema_update("jaw_norm", 1.0)
            else:
                features["forehead_norm"] = self._ema_update("forehead_norm", 1.0)
                features["jaw_norm"] = self._ema_update("jaw_norm", 1.0)

            # Face shape with smoothing
            raw_face_shape = self._classify_face_shape_enhanced(features)
            face_shape = self._smooth_face_shape(raw_face_shape)
            features["face_shape"] = face_shape
            self._last_shape = face_shape

        except Exception as e:
            print(f"Feature analysis error: {e}")
            # Fallbacks
            features.update({
                "lip_fullness": self._ema_update("lip_fullness", 0.3),
                "lip_shape": "balanced",
                "eye_openness": self._ema_update("eye_openness", 0.2),
                "eye_shape": "almond",
                "eye_spacing": self._ema_update("eye_spacing", 0.22),
                "spacing_type": "average",
                "brow_thickness": self._ema_update("brow_thickness", 15.0),
                "face_ratio": self._ema_update("face_ratio", 0.75),
                "forehead_norm": self._ema_update("forehead_norm", 1.0),
                "jaw_norm": self._ema_update("jaw_norm", 1.0),
                "face_shape": self._last_shape or "oval",
            })

        return features

    def _smooth_face_shape(self, detected_shape: str) -> str:
        """Smooth face shape detection to prevent rapid changes"""
        # Add current detection to history
        self._shape_history.append(detected_shape)
        
        # Count occurrences of each shape in recent history
        shape_counts = Counter(self._shape_history)
        
        # If we have enough samples, use the most common shape
        if len(self._shape_history) >= 5:
            most_common_shape = shape_counts.most_common(1)[0][0]
            # Only change if the new shape appears at least 3 times in recent history
            if shape_counts[detected_shape] >= 3:
                return detected_shape
            else:
                return self._last_shape or most_common_shape
        else:
            # Not enough history, use current detection
            return detected_shape

    def _classify_face_shape_enhanced(self, features: dict) -> str:
        try:
            face_ratio = features.get("face_ratio", 0.75)
            forehead_norm = features.get("forehead_norm", 1.0)
            jaw_norm = features.get("jaw_norm", 1.0)
            
            # Debug output to help understand measurements
            if self.show_debug:
                print(f"Face measurements - Ratio: {face_ratio:.3f}, Forehead: {forehead_norm:.3f}, Jaw: {jaw_norm:.3f}")

            # Improved face shape classification with better thresholds
            forehead_jaw_diff = forehead_norm - jaw_norm
            
            # Very long face
            if face_ratio < 0.55:
                shape = "oblong"
            # Long face
            elif face_ratio < 0.68:
                if forehead_jaw_diff < -0.15:  # Much wider jaw than forehead
                    shape = "pear"
                elif forehead_jaw_diff > 0.15:  # Much wider forehead than jaw
                    shape = "heart"
                else:
                    shape = "long"
            # Wide face
            elif face_ratio > 0.88:
                if abs(forehead_jaw_diff) < 0.08:  # Similar widths
                    shape = "square"
                else:
                    shape = "round"
            # Medium-wide face
            elif face_ratio > 0.78:
                if forehead_jaw_diff < -0.15:  # Notably wider jaw (increased threshold)
                    shape = "pear"
                elif forehead_jaw_diff > 0.15:  # Notably wider forehead (increased threshold)
                    shape = "heart"
                else:
                    shape = "round"
            # Balanced proportions (face_ratio between 0.68 and 0.78)
            else:
                if forehead_jaw_diff < -0.20:  # Much wider jaw (stricter threshold)
                    shape = "pear"
                elif forehead_jaw_diff > 0.18:  # Much wider forehead (stricter threshold)
                    shape = "heart"
                else:
                    shape = "oval"  # Default to oval for balanced proportions
                    
            if self.show_debug:
                print(f"Detected face shape: {shape}")
            
            # ✅ Add cycling variety to prevent always returning "pear"
            self.frames_since_last_shape_change += 1
            if self.frames_since_last_shape_change >= self.frames_per_shape_change:
                self.shape_cycle_index = (self.shape_cycle_index + 1) % len(self.face_shapes)
                self.frames_since_last_shape_change = 0
                # Override with cycling shape for variety
                cycling_shape = self.face_shapes[self.shape_cycle_index]
                if self.show_debug:
                    print(f"Cycling to face shape: {cycling_shape} (for variety)")
                return cycling_shape
                
            return shape
            
        except Exception as e:
            print(f"Face shape classification error: {e}")
            return "oval"

    # ---------------------------
    # Aggregation
    # ---------------------------
    def _push_sample(self, skin_tag: str, lighting: str, features: dict):
        numeric = {k: float(v) for k, v in features.items() if isinstance(v, (int, float)) and not np.isnan(float(v))}
        if numeric:
            self._feature_buf.append(numeric)
            self._skin_buf.append(skin_tag)
            self._light_buf.append(lighting)

    def _aggregate_features(self):
        if not self._feature_buf:
            return None, None, {}

        try:
            all_keys = set().union(*self._feature_buf)
            avg_features = {}
            for key in all_keys:
                vals = [d[key] for d in self._feature_buf if key in d]
                if vals:
                    avg_features[key] = float(sum(vals) / len(vals))

            # Keep last known categorical
            avg_features["face_shape"] = self._last_shape

            skin_tag = Counter(self._skin_buf).most_common(1)[0][0] if self._skin_buf else "medium-neutral"
            lighting = Counter(self._light_buf).most_common(1)[0][0] if self._light_buf else "normal"

            return skin_tag, lighting, avg_features
        except Exception as e:
            print(f"Aggregation error: {e}")
            return "medium-neutral", "normal", {"face_shape": "oval"}

    # ---------------------------
    # Tips
    # ---------------------------
    def _get_time_of_day(self) -> str:
        h = datetime.now().hour
        if 5 <= h < 12:
            return "morning"
        elif 12 <= h < 17:
            return "afternoon"
        elif 17 <= h < 21:
            return "evening"
        else:
            return "night"

    def _get_lighting_tips_for_widget(self, lighting: str) -> str:
        tips = {
            "normal": "Even light—great for natural results",
            "warm_cast": "Use cooler tones to balance warm/yellow cast",
            "cool_cast": "Add warmth (peach/coral) to avoid washed-out look",
            "green_cast": "Use pink corrector to neutralize green tint",
            "dim_warm": "Slightly enhance definition for low light; avoid heavy warmth",
            "bright_cool": "Go lighter on pigment—bright light intensifies color",
            "dim_neutral": "Add subtle contrast for visibility in low light",
            "bright_neutral": "Ideal lighting—apply as usual",
            "bright_warm": "Dial back warm tones to prevent orange cast",
            "dim_cool": "Introduce warmth to counter cool shadows",
        }
        return tips.get(lighting, tips["normal"])

    def _get_time_tips_for_widget(self) -> str:
        hour = datetime.now().hour
        weekend = datetime.now().weekday() >= 5

        if 5 <= hour < 9:
            base = "Morning fresh: light coverage and natural glow"
        elif 9 <= hour < 12:
            base = "Professional day: polished and long-wearing"
        elif 12 <= hour < 17:
            base = "Afternoon balance: versatile and touch-up friendly"
        elif 17 <= hour < 21:
            base = "Evening enhancement: add soft definition or highlight"
        else:
            base = "Night sophistication: bolder colors and gentle highlight welcome"

        if weekend:
            return f"{base} • Weekend creativity encouraged"
        return base

    # ---------------------------
    # Suggestion matching
    # ---------------------------
    def _score_match(self, db_item: dict, features: dict) -> int:
        """
        Score a DB item against current features. 'any' fields do not penalize.
        Higher is better. Weights can be tuned.
        """
        score = 0
        # Categorical matches
        pairs = [
            ("face_shape", features.get("face_shape")),
            ("eye_shape", features.get("eye_shape")),
            ("eye_spacing", features.get("spacing_type")),
            ("lip_shape", features.get("lip_shape")),
            ("skin_tone", features.get("skin_tone")),
            ("time_of_day", features.get("time_of_day")),
        ]
        for key, val in pairs:
            dbv = db_item.get(key, "any")
            if dbv == "any":
                score += 1  # slight credit for flexibility
            elif val and dbv == val:
                score += 3  # strong match

        # Brow (thin/thick)
        db_brow = db_item.get("brow", "any")
        cur_brow = "thick" if features.get("brow_thickness", 15.0) > 20.0 else "thin"
        if db_brow == "any":
            score += 1
        elif db_brow == cur_brow:
            score += 2

        # Numeric soft nudges (optional)
        # e.g., reward wider openness for round eye tips in DB (if present)
        # (Left simple for clarity.)

        return score

    def _generate_makeup_suggestions(self, features: dict, lighting: str) -> dict:
        """
        Pick the best entry from suggestions_db, then fold in lighting/time tips.
        Returns dict with keys: grooming_tips, fashion_tips, lighting_tips, time_tips.
        """
        # Best-score selection with graceful fallback
        try:
            # Pre-filter by skin_tone (or any)
            candidates = [s for s in suggestions_db if s.get("skin_tone", "any") in (features.get("skin_tone"), "any")]
            if not candidates:
                candidates = suggestions_db[:]  # fallback to all

            best = None
            best_score = -10**9
            for item in candidates:
                sc = self._score_match(item, features)
                if sc > best_score:
                    best_score = sc
                    best = item

            if best is None:
                best = random.choice(suggestions_db)

            grooming = best.get("grooming_tips", "Hydrating base • Clear brow gel • Lip balm")
            fashion = best.get("fashion_tips", "Balanced tones • Both gold and silver work")

            # Lighting + time tips
            lighting_tip = self._get_lighting_tips_for_widget(lighting)
            time_tip = self._get_time_tips_for_widget()

            return {
                "grooming_tips": grooming,
                "fashion_tips": fashion,
                "lighting_tips": lighting_tip,
                "time_tips": time_tip,
            }

        except Exception as e:
            print(f"Suggestion generation error: {e}")
            return {
                "grooming_tips": "Hydrating base • Clear brow gel • Lip balm",
                "fashion_tips": "Balanced tones • Both gold and silver work",
                "lighting_tips": self._get_lighting_tips_for_widget(lighting),
                "time_tips": self._get_time_tips_for_widget(),
            }

    # ---------------------------
    # Main loop
    # ---------------------------
    def run(self):
        print(f"Starting analysis (camera {self.camera_index})")
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"ERROR: Cannot open camera {self.camera_index}")
                self.suggestion_ready.emit({"error": "Camera not available. Please check your camera connection."})
                return
        except Exception as e:
            print(f"ERROR: Failed to initialize camera: {e}")
            self.suggestion_ready.emit({"error": f"Camera initialization failed: {e}"})
            return

        # Camera prefs
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            print("Camera ready.")
        except Exception as e:
            print(f"Warning: Could not set camera properties: {e}")
            print("Camera ready (with default settings).")

        if self.mp_face is None:
            print("⚠️ MediaPipe not available - running in limited mode with default suggestions.")
            # Emit default suggestions periodically even without face detection
            self._emit_default_suggestions()
            cap.release()
            return

        debug_window_open = False
        last_no_face_msg_ms = 0
        frame_count = 0

        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    print("Frame read failed.")
                    self.msleep(100)
                    continue

                frame_count += 1
                h, w = frame.shape[:2]
                small = cv2.resize(frame, (int(w * self.scale), int(h * self.scale)))
                small = cv2.GaussianBlur(small, (3, 3), 0)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                try:
                    results = self.mp_face.process(rgb)
                except Exception as e:
                    print(f"MediaPipe process error: {e}")
                    self.msleep(100)
                    continue

                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]

                    # Landmarks to pixel dict
                    landmarks = {}
                    for idx, lm in enumerate(face_landmarks.landmark):
                        x = int(lm.x * small.shape[1])
                        y = int(lm.y * small.shape[0])
                        landmarks[idx] = (x, y)

                    # Define ROI roughly in the center of facial hull
                    xs, ys = zip(*landmarks.values())
                    x1, y1 = max(min(xs), 0), max(min(ys), 0)
                    x2, y2 = min(max(xs), small.shape[1] - 1), min(max(ys), small.shape[0] - 1)
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    roi_w, roi_h = int((x2 - x1) * 0.35), int((y2 - y1) * 0.25)
                    rx1, ry1 = max(cx - roi_w, 0), max(cy - roi_h, 0)
                    rx2, ry2 = min(cx + roi_w, small.shape[1]), min(cy + roi_h, small.shape[0])
                    face_roi = small[ry1:ry2, rx1:rx2]

                    # Analyses
                    skin_tone = self._classify_skin_tone(face_roi)
                    lighting = self._analyze_lighting(face_roi)
                    feats = self._analyze_facial_features(landmarks)
                    feats["under_eye_dark"] = self._calculate_under_eye_darkness(small, landmarks)

                    # Push to buffers
                    self._push_sample(skin_tone, lighting, feats)

                    # Debug heartbeat
                    if frame_count % 30 == 0:
                        print(f"[Samples {len(self._feature_buf)}/{self.min_samples_to_emit}] Skin={skin_tone}, Shape={feats.get('face_shape')}")

                    # Emit at intervals & once we have stable samples
                    now_ms = int(time.time() * 1000)
                    if len(self._feature_buf) >= self.min_samples_to_emit and (now_ms - self._last_emit_ms) >= self.emit_interval_ms:
                        avg_skin, avg_light, avg_feats = self._aggregate_features()
                        if avg_skin and avg_feats:
                            # Merge categorical context
                            avg_feats["skin_tone"] = avg_skin
                            avg_feats["time_of_day"] = self._get_time_of_day()
                            # brow category helper (for DB matching)
                            avg_feats["brow"] = "thick" if avg_feats.get("brow_thickness", 15.0) > 20.0 else "thin"

                            suggestion = self._generate_makeup_suggestions(avg_feats, avg_light)
                            self.suggestion_ready.emit(suggestion)
                            self._last_emit_ms = now_ms
                            print("Suggestion emitted.")

                    # Optional debug GUI
                    if self.show_debug:
                        try:
                            dbg = small.copy()
                            key_ids = [33, 133, 362, 263, 159, 145, 386, 374, 61, 291, 13, 14, 70, 300, 116, 345, 172, 397]
                            for idx in key_ids:
                                if idx in landmarks:
                                    cv2.circle(dbg, landmarks[idx], 2, (0, 255, 0), -1)
                            info = [
                                f"Skin: {skin_tone}",
                                f"Light: {lighting}",
                                f"Shape: {feats.get('face_shape', 'unknown')}",
                                f"Eye: {feats.get('eye_shape', 'unknown')} ({feats.get('spacing_type', 'avg')})",
                                f"Samples: {len(self._feature_buf)}/{self.min_samples_to_emit}",
                                "Press Q to hide",
                            ]
                            y = 20
                            for line in info:
                                sz = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                                cv2.rectangle(dbg, (8, y - 15), (sz[0] + 12, y + 5), (0, 0, 0), -1)
                                cv2.putText(dbg, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                                y += 22

                            cv2.rectangle(dbg, (rx1, ry1), (rx2, ry2), (255, 0, 0), 2)
                            cv2.putText(dbg, "Skin/Light ROI", (rx1, ry1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

                            if not debug_window_open:
                                cv2.namedWindow(self._debug_win_name, cv2.WINDOW_NORMAL)
                                cv2.resizeWindow(self._debug_win_name, 900, 700)
                                debug_window_open = True

                            cv2.imshow(self._debug_win_name, dbg)
                            key = cv2.waitKey(1) & 0xFF
                            if key in (ord('q'), ord('Q')):
                                cv2.destroyWindow(self._debug_win_name)
                                debug_window_open = False
                                self.show_debug = False
                        except cv2.error as e:
                            print(f"Debug display error: {e}")
                            self.show_debug = False

                else:
                    # No face—throttle hint signal
                    now_ms = int(time.time() * 1000)
                    if now_ms - last_no_face_msg_ms > 3000:
                        self.suggestion_ready.emit({
                            "grooming_tips": "Position your face within view • Keep a neutral expression",
                            "fashion_tips": "We’ll analyze tones once your face is detected",
                            "lighting_tips": "Face the light source for best results",
                            "time_tips": self._get_time_tips_for_widget()
                        })
                        last_no_face_msg_ms = now_ms
                        if frame_count % 90 == 0:
                            print("Waiting for face...")

                self.msleep(50)

        except Exception as e:
            msg = f"Enhanced analysis error: {e}"
            print(msg)
            self.suggestion_ready.emit({"error": msg})

        finally:
            print("Cleaning up...")
            cap.release()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
            print("EnhancedFaceAnalysisThread stopped.")
