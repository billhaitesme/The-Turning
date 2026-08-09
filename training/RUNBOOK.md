# Training runbook — consolidation → adapter → served model

State as of 2026-08-08 late (first tutelage training run, ADR 0024):

- **v1 adapter DONE + chain PROVEN**: trained (32 steps), converted to GGUF, and served —
  `ollama create omega-arc-tutored` succeeded and the model answers. But 4 epochs was too weak a
  signal (final loss 4.46): answers were generic, not the studied ones.
- **v2 OUTCOME (2026-08-09): crashed at step ~100/320** — native crash, almost certainly VRAM
  contention (Ollama model loads during training). BUT checkpoint-100 (~12.5 epochs) was converted
  and served: the proof visibly landed — "Machine ID is O3M3G4ARC" (studied fact, slightly garbled),
  "superseded memories aren't deleted; they're hidden" (correct paraphrase). Knowledge is in the
  weights; the identity string needs the full run to come out exact.
- **CHAIN CLOSED (2026-08-09): v4 clean bf16 run completed — 320 steps, final step loss 0.060,
  token accuracy 98.2%. PROOF: 5/5 quiz answers VERBATIM from bare weights through the full served
  chain** (Ollama API, temperature 0). Adapter registry: marked trained, ACTIVATED. Two hard-won
  rules for every future run:
  1. **bf16, never fp16** on this host — both fp16 runs (v2, v3) died in native GradScaler crashes;
     the clean bf16 run sailed through. train_adapter.py now auto-selects bf16 + saves every 25.
  2. **Serve adapters on an fp16/high-precision base, never q4** — the v4 adapter was verbatim
     perfect HF-side (probe_adapter_hf.py proves it) but confabulated on qwen2.5:3b-instruct (q4);
     on qwen2.5:3b-instruct-fp16 it is verbatim perfect. A bf16-trained LoRA loses its deltas over
     4-bit weights. Modelfile: FROM qwen2.5:3b-instruct-fp16, temperature 0 for recall-style use.
- (superseded) **v3 WAS IN FLIGHT, DETACHED + OFFLINE + GPU-EXCLUSIVE** (all Ollama models stopped first — the lesson
  from v2): output `adapters/...-v3/`, log `train_v3_detached.log`. On `adapter saved` + `EXIT=0`,
  repeat convert→Modelfile→create→proof against -v3. RULE: never run Ollama generations while
  training.
- (superseded) **v2 retrain WAS IN FLIGHT, DETACHED + OFFLINE** (`HF_HUB_OFFLINE=1` — needs no internet): 40 epochs
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

## The voice experiment — QLoRA on the 12B (2026-08-09)

First attempt to consolidate onto the VOICE family: the same 16-pair artifact trained as QLoRA
against `huihui-ai/Huihui-gemma-4-12B-it-abliterated` (the publisher-matched HF original of the
default voice `huihui_ai/gemma-4-abliterated:12b`). Run: NF4 double-quant base, bf16 compute,
r=8/alpha=16, 320 steps, loss 9.23 -> 0.103, token acc 94%, 35 min on the 8 GB card.

Three new standing rules, each paid for with a crashed run:

1. **NF4 layers never leave the GPU.** bitsandbytes cannot execute 4-bit modules from CPU; if
   `device_map="auto"` spills quantized layers, dispatch dies on meta tensors. Use an explicit
   map: ALL quantized decoder layers -> GPU; the big unquantized pieces (embed_tokens ~2 GB, its
   tied lm_head, embed_vision, embed_audio) -> CPU. That is what fits 12B QLoRA in 8 GB.
2. **Multimodal bases: pass the tokenizer to SFTTrainer explicitly** (`processing_class=`).
   Otherwise trl auto-loads the image/audio Processor (wants PIL, drags towers into
   preprocessing). Text-only SFT needs neither. (pillow is installed now anyway.)
3. **CPU-offloaded lm_head breaks trl's default `chunked_nll` loss** (it patches
   `lm_head.forward`, which accelerate has already wrapped in a `functools.partial`).
   `loss_type="nll"` — identical math at our tiny sequence lengths.

Bonus rule for this host: PowerShell `*>` redirection writes UTF-16LE logs — bash `grep` sees
binary and silently matches nothing. Monitors must `iconv -f UTF-16LE -t UTF-8` first.

### Served result (adapter over Q4_K_M base tag): PARTIAL — 2.5/5

Q1 identity verbatim; Q3 (never deleted) correct; Q5 nearly right ("embeddingg4" — a smeared
"embeddinggemma"); Q2/Q4 confabulated. Better than the qwen bf16-adapter-over-q4 failure mode
(which inverted answers), consistent with the codebook gap: the adapter compensated NF4's error
surface, the serve-side base is Q4_K_M (256-block k-quant vs NF4's 64-block codebook).
HF-side probe over the exact NF4 training base: see below.

### The fidelity ladder (final, 2026-08-09)

| Serving arrangement | Score |
|---|---|
| Adapter over NF4 (the exact training base) | 4.5/5 |
| Merged into bf16 -> quantized Q8_0 | ~3.5/5 |
| Merged into bf16 -> quantized Q4_K_M (`omega-arc-voice-12bq`) | ~3.5/5 |
| Adapter GGUF over the Q4_K_M tag (`omega-arc-tutored-12bq`) | 2.5/5 |

Q8 == Q4 within noise -> the loss is at the MERGE boundary, not the final quant depth: QLoRA
deltas compensate NF4's specific error surface; re-applied to clean bf16 they misfire slightly,
and requantization adds its own noise. The serve-side knob is exhausted — the remaining knob is
TRAINING MARGIN. Next iteration when scheduled: r=16/alpha=32, 60-80 epochs, target loss < 0.05
(the qwen 5/5 run hit 0.060; this run stopped at 0.103). Expect NF4-side 5/5 with margin ->
merged+Q4_K_M near-verbatim.

Chain status: **train -> merge -> quantize -> serve PROVEN on the voice family, end to end.**
Artifacts kept: HF base + merged shards + f16 GGUF under training/hf-bases/ (disk is cheap,
re-merging is 30 min); candidates `omega-arc-voice-12bq` (merged Q4_K_M) and
`omega-arc-tutored-12bq` (adapter form) live in Ollama for the operator to poke.
Perspective: bare-weights recall is the redundancy layer — the runtime's primary path to its
studied knowledge remains memory retrieval (12/12 with notes). Consolidation compounds; it does
not need to be perfect on day one.

### Rules 5-6 — sharing the card with a life (2026-08-09)

5. **CPU-parked layers cannot carry LoRA.** accelerate's offload hooks materialize weights at
   forward time; parameter gradients cannot flow back into them (backward dies with
   "expected device meta but got cuda:0"). Layers parked for VRAM headroom must be excluded from
   `target_modules` — frozen scenery, like the embedding and towers.
6. **Leave the desktop its share of VRAM.** Packing the card to ~7.4/8 GB crashes the WHOLE
   MACHINE when a browser asks for compositing memory: nvlddmkm (the NVIDIA kernel driver) falls
   over and the host hard-reboots (Event 153/14 + Kernel-Power 41, three times on 2026-08-08/09).
   `--cpu-layers N` parks the last N decoder layers on CPU unquantized. 14 layers leaves ~500 MB
   free with Firefox open — survivable but tight; the driver still died once on a spike. Run
   training at BelowNormal priority (the CPU legs otherwise starve the desktop and feel like
   "slow internet"), and treat kills as cheap: checkpoints every 25 steps mean a machine crash
   costs at most ~3 minutes. Resume with `--resume <output>\checkpoint-NNN` (same dtype resumes
   cleanly; the fp16/bf16 cross-resume ban from Stage 2 still applies).
