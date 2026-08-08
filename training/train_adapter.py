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
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer
import torch

parser = argparse.ArgumentParser()
parser.add_argument("--data", required=True, help="distillation JSONL (messages format)")
parser.add_argument("--output", required=True, help="adapter output directory")
parser.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct", help="HF base model")
parser.add_argument("--epochs", type=float, default=4, help="tiny datasets need a few passes")
args = parser.parse_args()

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

tokenizer = AutoTokenizer.from_pretrained(args.base, use_fast=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float16).to("cuda")

peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

dataset = load_dataset("json", data_files=args.data, split="train")
print("training pairs:", len(dataset))

train_args = TrainingArguments(
    output_dir=args.output,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=2,
    num_train_epochs=args.epochs,
    learning_rate=2e-4,
    logging_steps=1,
    save_steps=100,
    save_total_limit=1,
    fp16=True,
    report_to="none",
)

trainer = SFTTrainer(model=model, train_dataset=dataset, args=train_args)
trainer.train()
trainer.save_model(args.output)
tokenizer.save_pretrained(args.output)
print("adapter saved to", Path(args.output).resolve())
