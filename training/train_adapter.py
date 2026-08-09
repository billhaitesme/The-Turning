"""Train a LoRA adapter from a tutelage distillation artifact (Epoch XI-C, ADR 0024).

Operator-executed by design — the runtime assembles and gates the data; a human runs this.

  .venv\\Scripts\\python.exe train_adapter.py --data distillation/<artifact>.jsonl --output adapters/<id>

Deliberately close to the proven identity run (train.py): same base model family, same
LoRA shape. The dataset is chat-format JSONL ({"messages": [...]}) as produced by the
consolidation gate — only key-verified answers ever reach this script.
"""
import argparse
from pathlib import Path

from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTConfig, SFTTrainer
import torch

parser = argparse.ArgumentParser()
parser.add_argument("--data", required=True, help="distillation JSONL (messages format)")
parser.add_argument("--output", required=True, help="adapter output directory")
parser.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct", help="HF base model")
parser.add_argument("--epochs", type=float, default=4, help="tiny datasets need a few passes")
parser.add_argument("--resume", default=None, help="checkpoint dir to resume from")
parser.add_argument("--save-steps", type=int, default=25, help="frequent saves: crashes lose little")
parser.add_argument("--qlora", action="store_true",
                    help="NF4-quantize the frozen base (QLoRA) — for bases too big for bf16 on this card")
parser.add_argument("--lora-r", type=int, default=8, help="LoRA rank (alpha rides at 2x)")
parser.add_argument("--cpu-layers", type=int, default=0,
                    help="qlora only: park the LAST N decoder layers on CPU (unquantized) to leave "
                         "VRAM headroom for the desktop/browser — the host crashed twice from "
                         "Firefox contending with a packed card")
args = parser.parse_args()

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

tokenizer = AutoTokenizer.from_pretrained(args.base, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# bf16 on Blackwell: no GradScaler (fp16 scaler runs crashed natively twice on this host)
DTYPE = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
print("dtype:", DTYPE, "| qlora:", args.qlora)

if args.qlora:
    # Matched-precision experiment: train against a 4-bit base so the adapter learns over
    # quantized weights, then serve over the (4-bit) Ollama tag. NF4 != Q4_K_M — approximate match.
    from transformers import AutoConfig
    n_layers = AutoConfig.from_pretrained(args.base).text_config.num_hidden_layers
    cpu_layer_ids = list(range(n_layers - args.cpu_layers, n_layers))
    # Layers parked on CPU must stay UNQUANTIZED (bnb cannot run 4-bit modules from CPU),
    # so they join the skip list and ride bf16.
    skip = ["embed_vision", "embed_audio", "lm_head"] + [
        f"language_model.layers.{i}" for i in cpu_layer_ids
    ]
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=DTYPE,
        bnb_4bit_use_double_quant=True,
        llm_int8_skip_modules=skip,
        llm_int8_enable_fp32_cpu_offload=True,
    )
    # Explicit placement: every NF4-quantized decoder layer sits on the GPU. The unquantized
    # pieces go to CPU: the 2 GB embedding, the tied lm_head (same tensor), the multimodal
    # towers, and the last --cpu-layers decoder layers (VRAM headroom for the desktop).
    device_map = {
        "": 0,
        "model.language_model.embed_tokens": "cpu",
        "model.embed_vision": "cpu",
        "model.embed_audio": "cpu",
        "lm_head": "cpu",
    }
    for i in cpu_layer_ids:
        device_map[f"model.language_model.layers.{i}"] = "cpu"
    print(f"layers: {n_layers} total, {len(cpu_layer_ids)} on CPU {cpu_layer_ids or ''}")
    model = AutoModelForCausalLM.from_pretrained(
        args.base,
        torch_dtype=DTYPE,
        quantization_config=bnb_config,
        device_map=device_map,
    )
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    print("device map:", {k: str(v) for k, v in model.hf_device_map.items()} if hasattr(model, "hf_device_map") else "n/a")
else:
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=DTYPE).to("cuda")

if args.qlora:
    # gemma4-unified reuses q_proj/... names inside the vision/audio towers; scope to the text
    # stack — convert_lora_to_gguf rejects tower/embedding deltas anyway. CPU-parked layers are
    # also excluded: accelerate offload-hooks cannot receive parameter gradients (meta-device
    # backward error), so only GPU-resident layers carry LoRA.
    gpu_layer_ids = "|".join(str(i) for i in range(n_layers - args.cpu_layers))
    target = (r".*language_model.*\.layers\.(?:" + gpu_layer_ids +
              r")\.(?:self_attn|mlp)\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$")
else:
    target = None

peft_config = LoraConfig(
    r=args.lora_r,
    lora_alpha=2 * args.lora_r,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=target,
)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

dataset = load_dataset("json", data_files=args.data, split="train")
print("training pairs:", len(dataset))

train_args = SFTConfig(
    # trl's default chunked_nll loss patches lm_head.forward assuming a bound method; with the
    # head CPU-offloaded (accelerate hook = functools.partial) that patch crashes. Same math.
    loss_type="nll" if args.qlora else "chunked_nll",
    output_dir=args.output,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=2,
    num_train_epochs=args.epochs,
    learning_rate=2e-4,
    logging_steps=1,
    save_steps=args.save_steps,
    save_total_limit=2,
    bf16=DTYPE == torch.bfloat16,
    fp16=DTYPE == torch.float16,
    optim="paged_adamw_8bit" if args.qlora else "adamw_torch",
    report_to="none",
)

# pass the tokenizer explicitly: on multimodal bases trl would otherwise auto-load the
# image/audio Processor (needs PIL, pulls towers into preprocessing) — text-only SFT wants neither
trainer = SFTTrainer(model=model, train_dataset=dataset, args=train_args, processing_class=tokenizer)
trainer.train(resume_from_checkpoint=args.resume)
trainer.save_model(args.output)
tokenizer.save_pretrained(args.output)
print("adapter saved to", Path(args.output).resolve())
