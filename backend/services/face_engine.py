"""Face engine — detection, embedding, and the enrolled gallery (faces slice, 2026-11-05).

Built for Ø2-02 before Ø2-02: the exact same ONNX models (InsightFace's official SCRFD detector
+ ArcFace recognizer, published by the maintainers) run here on CPU via onnxruntime and later on
the dog's Jetson — tune the thresholds on the PC, carry the gallery over. No compiled face
packages, no third-party binary wheels: the models are data under backend/models/faces/, the
code is the runtime's own.

Doctrine:
  * A vision LLM DESCRIBES a face; this engine IDENTIFIES one — against an operator-enrolled
    gallery only. No gallery entry, no identity: strangers are "unknown", never guessed.
  * Enrollment is an OPERATOR action from a console. The seat can ask who is in an image
    (recognize_faces); it cannot add anyone to the gallery.
  * The gallery is biometric data: it lives in the runtime's local data dir, is never committed,
    and never rides any non-local seat or rung.
"""
from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from services.tool_contracts import utc_now_iso

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "faces"
DET_MODEL = "det_10g.onnx"        # SCRFD-10G-KPS (buffalo_l); det_500m.onnx on the dog
REC_MODEL = "w600k_r50.onnx"      # ArcFace ResNet50 (buffalo_l); w600k_mbf.onnx on the dog
DET_SIZE = 640
DET_SCORE_THRESHOLD = 0.5
MATCH_THRESHOLD = 0.40            # cosine similarity on normed ArcFace embeddings; tune here
MAX_FACES = 16

# ArcFace's canonical 5-point destination (112x112 alignment template).
ARCFACE_DST = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
     [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float32)


class FaceEngineUnavailable(RuntimeError):
    """Raised when the engine's models or image library are not present yet."""


def _gallery_path() -> Path:
    from services import tool_contracts as _tc
    return _tc.TOOL_DATA_DIR / "faces" / "gallery.json"


def load_gallery() -> Dict[str, Any]:
    path = _gallery_path()
    if not path.exists():
        return {"version": 1, "people": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "people": []}
    return data if isinstance(data, dict) else {"version": 1, "people": []}


def save_gallery(gallery: Dict[str, Any]) -> None:
    path = _gallery_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gallery, indent=2, ensure_ascii=False), encoding="utf-8")


def list_people() -> List[Dict[str, Any]]:
    return [{"person_id": p.get("person_id"), "name": p.get("name"),
             "samples": len(p.get("embeddings") or []), "enrolled_at": p.get("enrolled_at")}
            for p in load_gallery().get("people", [])]


def remove_person(person_id: str) -> bool:
    gallery = load_gallery()
    before = len(gallery.get("people", []))
    gallery["people"] = [p for p in gallery.get("people", []) if p.get("person_id") != person_id]
    save_gallery(gallery)
    return len(gallery["people"]) < before


# --------------------------------------------------------------------------- the ONNX engine
class OnnxFaceEngine:
    """SCRFD detection + ArcFace embedding on onnxruntime. Lazy; CPU; Jetson-portable."""

    def __init__(self) -> None:
        self._det = None
        self._rec = None
        self._cv2 = None

    def _ensure(self) -> None:
        if self._det is not None:
            return
        try:
            import cv2  # opencv-python-headless
        except ImportError as exc:
            raise FaceEngineUnavailable("opencv-python-headless is not installed yet.") from exc
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise FaceEngineUnavailable("onnxruntime is not installed.") from exc
        det_path = MODEL_DIR / DET_MODEL
        rec_path = MODEL_DIR / REC_MODEL
        if not det_path.exists() or not rec_path.exists():
            raise FaceEngineUnavailable(
                f"Face models missing under {MODEL_DIR} ({DET_MODEL} + {REC_MODEL} from the "
                "official InsightFace buffalo_l pack).")
        try:
            self._det = ort.InferenceSession(str(det_path), providers=["CPUExecutionProvider"])
            self._rec = ort.InferenceSession(str(rec_path), providers=["CPUExecutionProvider"])
        except Exception as exc:  # noqa: BLE001 — a partial download reports plainly
            raise FaceEngineUnavailable(f"Face models unreadable (incomplete download?): {exc}") from exc
        self._cv2 = cv2

    # ---------------- detection (SCRFD, anchor-free, strides 8/16/32, KPS head)
    def _detect(self, image: "np.ndarray") -> List[Dict[str, Any]]:
        cv2 = self._cv2
        height, width = image.shape[:2]
        scale = min(DET_SIZE / width, DET_SIZE / height)
        new_w, new_h = int(round(width * scale)), int(round(height * scale))
        resized = cv2.resize(image, (new_w, new_h))
        canvas = np.zeros((DET_SIZE, DET_SIZE, 3), dtype=np.uint8)
        canvas[:new_h, :new_w] = resized
        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128.0, (DET_SIZE, DET_SIZE),
                                     (127.5, 127.5, 127.5), swapRB=True)
        outputs = self._det.run(None, {self._det.get_inputs()[0].name: blob})
        # SCRFD with KPS emits 9 outputs: scores x3, bboxes x3, kps x3 (strides 8, 16, 32)
        strides = (8, 16, 32)
        candidates: List[Tuple[float, np.ndarray, np.ndarray]] = []
        for i, stride in enumerate(strides):
            scores = outputs[i].reshape(-1)
            bboxes = outputs[i + 3].reshape(-1, 4) * stride
            kpss = outputs[i + 6].reshape(-1, 10) * stride
            grid = DET_SIZE // stride
            anchor_centers = np.stack(
                np.mgrid[:grid, :grid][::-1], axis=-1).astype(np.float32).reshape(-1, 2) * stride
            anchor_centers = np.repeat(anchor_centers, 2, axis=0)  # 2 anchors per cell
            keep = scores >= DET_SCORE_THRESHOLD
            for center, score, bbox, kps in zip(anchor_centers[keep], scores[keep],
                                                bboxes[keep], kpss[keep]):
                x1, y1 = center[0] - bbox[0], center[1] - bbox[1]
                x2, y2 = center[0] + bbox[2], center[1] + bbox[3]
                points = np.stack([center[0] + kps[0::2], center[1] + kps[1::2]], axis=-1)
                candidates.append((float(score), np.array([x1, y1, x2, y2]) / scale,
                                   points / scale))
        candidates.sort(key=lambda c: c[0], reverse=True)
        kept: List[Dict[str, Any]] = []
        for score, box, kps in candidates:
            if len(kept) >= MAX_FACES:
                break
            if any(_iou(box, k["bbox"]) > 0.4 for k in kept):
                continue
            kept.append({"score": score, "bbox": box, "kps": kps})
        return kept

    # ---------------- embedding (ArcFace on the 5-point-aligned 112x112 crop)
    def _embed(self, image: "np.ndarray", kps: "np.ndarray") -> "np.ndarray":
        cv2 = self._cv2
        matrix, _ = cv2.estimateAffinePartial2D(kps.astype(np.float32), ARCFACE_DST,
                                                method=cv2.LMEDS)
        aligned = cv2.warpAffine(image, matrix, (112, 112))
        blob = cv2.dnn.blobFromImage(aligned, 1.0 / 127.5, (112, 112),
                                     (127.5, 127.5, 127.5), swapRB=True)
        embedding = self._rec.run(None, {self._rec.get_inputs()[0].name: blob})[0].reshape(-1)
        norm = np.linalg.norm(embedding)
        return embedding / norm if norm > 0 else embedding

    def faces_in(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Detect + embed every face in one image. Returns bbox/score/embedding per face."""
        self._ensure()
        cv2 = self._cv2
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode the image.")
        results = []
        for face in self._detect(image):
            embedding = self._embed(image, face["kps"])
            results.append({"bbox": [round(float(v), 1) for v in face["bbox"]],
                            "det_score": round(face["score"], 3),
                            "embedding": embedding})
        return results


def _iou(a: "np.ndarray", b) -> float:
    b = np.asarray(b, dtype=np.float32)
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


_engine: Optional[OnnxFaceEngine] = None


def get_engine() -> OnnxFaceEngine:
    global _engine
    if _engine is None:
        _engine = OnnxFaceEngine()
    return _engine


# --------------------------------------------------------------------------- enroll + match
def enroll(name: str, image_bytes: bytes, *, engine: Optional[Any] = None) -> Dict[str, Any]:
    """Operator enrolls one person from one clear photo (exactly one face expected)."""
    name = str(name or "").strip()
    if not name or len(name) > 60:
        raise ValueError("Enrollment needs a name (1-60 chars).")
    eng = engine or get_engine()
    faces = eng.faces_in(image_bytes)
    if not faces:
        raise ValueError("No face found in the enrollment photo.")
    if len(faces) > 1:
        raise ValueError(f"{len(faces)} faces found — enroll from a photo with exactly one.")
    embedding = [round(float(v), 6) for v in faces[0]["embedding"]]
    gallery = load_gallery()
    people = gallery.setdefault("people", [])
    existing = next((p for p in people if str(p.get("name", "")).lower() == name.lower()), None)
    if existing:
        existing.setdefault("embeddings", []).append(embedding)
        existing["embeddings"] = existing["embeddings"][-8:]  # keep the freshest samples
        entry = existing
    else:
        entry = {"person_id": f"face-{uuid.uuid4().hex[:10]}", "name": name,
                 "embeddings": [embedding], "enrolled_at": utc_now_iso()}
        people.append(entry)
    save_gallery(gallery)
    return {"person_id": entry["person_id"], "name": entry["name"],
            "samples": len(entry["embeddings"])}


def recognize(image_bytes: bytes, *, engine: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Every face in the image, matched against the enrolled gallery. Unknown stays unknown."""
    eng = engine or get_engine()
    gallery = load_gallery().get("people", [])
    results = []
    for face in eng.faces_in(image_bytes):
        embedding = np.asarray(face["embedding"], dtype=np.float32)
        best_name, best_sim = None, -1.0
        for person in gallery:
            for sample in person.get("embeddings") or []:
                sim = float(np.dot(embedding, np.asarray(sample, dtype=np.float32)))
                if sim > best_sim:
                    best_name, best_sim = person.get("name"), sim
        matched = best_sim >= MATCH_THRESHOLD
        results.append({
            "bbox": face["bbox"],
            "det_score": face["det_score"],
            "name": best_name if matched else "unknown",
            "similarity": round(best_sim, 3) if best_sim > -1.0 else None,
            "matched": matched,
        })
    return results
