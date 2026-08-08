"""Diagnostic: generate with the trained adapter HF-side (same weights it trained against).
Separates adapter-capacity problems from GGUF/quantization fidelity loss."""
import sys

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER = sys.argv[1] if len(sys.argv) > 1 else "adapters/adapter-omega-arc-architecture-20260808T112646-v4"

QUESTIONS = [
    "What is the machine identity of the runtime?",
    "Who may change the active language model, and how?",
    "Are superseded memories deleted?",
    "What is the desktop Bridge Zero and does it have chat?",
    "What produces the embeddings used for memory recall?",
]

DTYPE = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
tok = AutoTokenizer.from_pretrained(BASE, use_fast=True)
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=DTYPE).to("cuda")
model = PeftModel.from_pretrained(model, ADAPTER)
model.eval()

for q in QUESTIONS:
    messages = [
        {"role": "system", "content": "You are 0M3-G4-ARC. Answer from your studied knowledge."},
        {"role": "user", "content": q},
    ]
    inputs = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                     return_dict=True, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=80, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    answer = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Q: {q}")
    print(f"A: {answer.strip()[:180]}")
    print()
