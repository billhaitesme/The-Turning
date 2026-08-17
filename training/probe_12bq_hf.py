"""Probe the 12bq QLoRA adapter over the exact NF4 base it trained on (greedy, bare weights)."""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

BASE = "hf-bases/huihui-gemma-4-12b-it-abliterated"
import sys
ADAPTER = sys.argv[1] if len(sys.argv) > 1 else "adapters/adapter-omega-arc-architecture-20260809-12bq-v1"
QS = ["What is the machine identity of the runtime?",
      "Who may change the active language model, and how?",
      "Are superseded memories deleted?",
      "What is the desktop Bridge Zero and does it have chat?",
      "What produces the embeddings used for memory recall?"]

tok = AutoTokenizer.from_pretrained(BASE, use_fast=True)
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
                         llm_int8_skip_modules=["embed_vision", "embed_audio", "lm_head"],
                         llm_int8_enable_fp32_cpu_offload=True)
model = AutoModelForCausalLM.from_pretrained(
    BASE, torch_dtype=torch.bfloat16, quantization_config=bnb,
    device_map={"": 0, "model.language_model.embed_tokens": "cpu",
                "model.embed_vision": "cpu", "model.embed_audio": "cpu", "lm_head": "cpu"})
model = PeftModel.from_pretrained(model, ADAPTER)
model.eval()

for i, q in enumerate(QS, 1):
    messages = [{"role": "system", "content": "You are 0M3-G4-ARC. Answer from your studied knowledge."},
                {"role": "user", "content": q}]
    inputs = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                     return_dict=True, return_tensors="pt")
    inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=80, do_sample=False)
    answer = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"Q{i}: {q}")
    print(f"A{i}: {answer.strip()[:220]}")
    print()
