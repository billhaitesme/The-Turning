# Training runbook — consolidation → adapter → served model

State as of 2026-08-08 late (first tutelage training run, ADR 0024):

- **v1 adapter DONE + chain PROVEN**: trained (32 steps), converted to GGUF, and served —
  `ollama create omega-arc-tutored` succeeded and the model answers. But 4 epochs was too weak a
  signal (final loss 4.46): answers were generic, not the studied ones.
- **v2 retrain IN FLIGHT, DETACHED + OFFLINE** (`HF_HUB_OFFLINE=1` — needs no internet): 40 epochs
  (~320 steps) for deliberate memorization. Log: `training/train_v2_detached.log`; output:
  `training/adapters/adapter-omega-arc-architecture-20260808T112646-v2/`. When it shows
  `adapter saved` + `EXIT=0`:
  1. Re-run Stage 3 step 1 (convert) against the **-v2** directory (use the local HF snapshot path
     under `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-3B-Instruct/snapshots/<hash>/` as --base).
  2. Update `Modelfile`'s ADAPTER line to the -v2 adapter.gguf, then
     `ollama create omega-arc-tutored -f Modelfile` (overwrites in place).
  3. Proof: `ollama run omega-arc-tutored "What is the machine identity of the runtime?"` —
     expect **0M3-G4-ARC** from bare weights. Free VRAM first if loads hang: `ollama stop <model>`.
  4. Registry: with the backend up, POST /system/tutelage/adapters/adapter-omega-arc-architecture-20260808T112646
     {"action":"mark-trained"} then {"action":"activate"}.

Original context:

- **Artifact:** `distillation/adapter-omega-arc-architecture-20260808T112646.jsonl` (16 key-verified pairs)
- **Env:** `training/.venv` (torch 2.11 cu128, CUDA verified on the RTX 5060) — rebuild with the
  Setup section below if missing.
- **Run in flight:** detached process writing `training/train_run_detached.log`
  (`HF_HUB_DISABLE_XET=1` set because the Xet CDN kept timing out on this connection; downloads
  resume automatically on retry). Output: `training/adapters/adapter-omega-arc-architecture-20260808T112646/`
- **Base for this run:** `Qwen/Qwen2.5-3B-Instruct` — chain-proving only. It is ALIGNED; the tutored
  model must NOT become the primary voice (see the model-workshop note; next run targets an
  uncensored base, e.g. the abliterated Llama-3.1-8B HF original via QLoRA).

## Setup (one-time)

```powershell
cd training
& "$env:LOCALAPPDATA\Python\pythoncore-3.13-64\python.exe" -m venv .venv
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python.exe -m pip install transformers peft trl datasets accelerate gguf sentencepiece
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
```

## Stage 2 — train (retry if the detached run failed)

```powershell
cd training
$env:HF_HUB_DISABLE_XET = "1"
.venv\Scripts\python.exe train_adapter.py --data distillation\<artifact>.jsonl --output adapters\<adapter-id> --epochs 4
```

Watch for: CUDA available True → trainable params ~0.1% → loss dropping over ~32 steps → "adapter saved".

## Stage 3 — convert, serve, activate

```powershell
# 1) HF LoRA -> GGUF adapter (base config comes from the HF cache)
.venv\Scripts\python.exe llama.cpp\convert_lora_to_gguf.py adapters\<adapter-id> --base Qwen/Qwen2.5-3B-Instruct --outfile adapters\<adapter-id>\adapter.gguf

# 2) Modelfile + create
@"
FROM qwen2.5:3b-instruct
ADAPTER ./adapters/<adapter-id>/adapter.gguf
SYSTEM You are 0M3-G4-ARC. Answer from your studied knowledge.
"@ | Set-Content Modelfile -Encoding ascii
ollama create omega-arc-tutored -f Modelfile

# 3) Proof: quiz question, NO notes provided — answer must come from weights
ollama run omega-arc-tutored "What is the machine identity of the runtime?"

# 4) Registry lifecycle (backend running)
# POST /system/tutelage/adapters/<adapter-id> {"action":"mark-trained"} then {"action":"activate"}
```

Add `omega-arc-tutored` to SELECTABLE_CHAT_MODELS only as a specialist — never primary (aligned base).
