# Faces — identification against the enrolled gallery (built for Ø2-02 before Ø2-02)

**Status:** Built 2026-11-05 on the PC, by operator direction: learn and tune the module here so
the dog onboards a known quantity. (ADR 0026's spirit: a sense, bounded, local, operator-gated.)

## Doctrine

- A vision LLM **describes** a face; this engine **identifies** one — and only against the
  operator-enrolled gallery. No enrollment, no identity: strangers are `"unknown"`, never
  guessed. The seat is ordered accordingly (recognize_faces' own note).
- **Enrollment is an operator console action** (`/system/faces/enroll`, the Gallery bay in the
  web console). The seat reads identities through the `recognize_faces` bounded tool; it has no
  write path to the gallery.
- The gallery is **biometric data**: it lives at `<tool-data>/faces/gallery.json`, is gitignored
  (`backend/data/faces/`), and never rides any non-local seat or rung.

## Engine

`services/face_engine.py` — no compiled face packages, no third-party binary wheels:

- **Models:** InsightFace's official ONNX files (maintainer-published release assets), run on
  onnxruntime CPU. PC pack = **buffalo_l**: `det_10g.onnx` (SCRFD-10G-KPS detector) +
  `w600k_r50.onnx` (ArcFace R50 recognizer), under `backend/models/faces/` (gitignored; fetch:
  `https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip`).
- **Pipeline:** SCRFD detect (640², strides 8/16/32, 2 anchors/cell, IoU-0.4 NMS, score ≥ 0.5)
  → 5-point similarity alignment to the ArcFace 112² template → normed 512-d embedding →
  cosine match against every enrolled sample. `MATCH_THRESHOLD = 0.40` — the tuning knob.
- Up to 8 samples kept per person (re-enrolling a name adds a sample; freshest kept).

## Tuning (do here, carry to the dog)

- False "unknown" on a known face → enroll 2–3 more samples (angles, lighting) before touching
  the threshold; then lower `MATCH_THRESHOLD` in small steps (0.40 → 0.36).
- False match on a stranger → raise it (0.40 → 0.45). Log real similarities before moving it.
- Small/far faces missed → the detector's `DET_SIZE`/score threshold, not the matcher.

## Ø2-02 onboarding path

1. Same code, same gallery format. Copy `face_engine.py` + the gallery JSON to the dog's stack.
2. Swap the model pack for **buffalo_s** (`det_500m.onnx` + `w600k_mbf.onnx` — same release
   asset scheme) for Jetson framerates; the constants at the top of the engine are the only
   change. Embeddings differ between packs — **re-enroll on the dog's pack** (or enroll on both
   packs here first; the gallery supports multiple samples per person).
3. onnxruntime runs on Jetson as-is; TensorRT execution provider is the later speed upgrade.
4. The dog's camera loop calls `recognize()` per sampled frame; OMEGA-ARC's vision seat stays
   the scene-understander. Identification fast and local on-dog; description slow and rich.
