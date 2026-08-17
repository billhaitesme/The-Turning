# Lesson 1 — The Training Chain

Weight training is the one change to the runtime that touches the model itself, and it is
operator-executed: the runtime assembles, gates, versions, and records — it never trains. The
consolidation gate produces a distillation artifact of key-verified pairs; from there the chain is
train, convert, serve, prove, activate. Train a LoRA adapter with training/train_adapter.py;
convert it with convert_lora_to_gguf; write a Modelfile; create the served model with ollama create;
prove it by answering the quiz with no notes — verbatim from bare weights; then mark the adapter
trained and activate it in the registry. The tutored model is a specialist and is never the
primary voice.

Every rule in the runbook was paid for with a crashed run. Train in bf16, never fp16 — both fp16
runs died in GradScaler crashes on this host. Serve adapters on an fp16 or high-precision base,
never on a q4 quantized base — a bf16-trained adapter loses its deltas over four-bit weights and
confabulates, while over the fp16 base the same adapter is verbatim perfect. Never run Ollama
generations while training — the two fight for the same eight-gigabyte card. Set
HF_HUB_DISABLE_XET to 1 before downloads, because the Xet CDN times out on this connection.

The twelve-billion voice trains only as QLoRA, and its rules are stricter. NF4-quantized layers
never leave the GPU, because bitsandbytes cannot execute four-bit modules from the CPU; use an
explicit device map: all quantized decoder layers on the GPU, and the big unquantized pieces —
embed_tokens and its tied lm_head, the vision and audio embeddings — on the CPU. Multimodal bases
need the tokenizer passed to the trainer explicitly as processing_class, or the trainer loads the
image processor and drags the vision towers into preprocessing. A CPU-offloaded lm_head breaks the
default chunked loss, so use loss_type nll. Warm-start polish legs with --init-adapter at a lower
learning rate, and the LoRA rank must match the checkpoint being warm-started.

One bonus rule for this host: PowerShell's *> redirection writes UTF-16LE logs, so bash grep sees
binary and silently matches nothing — convert with iconv first.
