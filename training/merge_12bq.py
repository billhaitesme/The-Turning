"""Merge the 12bq QLoRA adapter into the bf16 base (CPU) and save sharded."""
import torch
from transformers import AutoModelForCausalLM
from peft import PeftModel

BASE = "hf-bases/huihui-gemma-4-12b-it-abliterated"
ADAPTER = "adapters/adapter-omega-arc-architecture-20260809-12bq-v1"
OUT = "hf-bases/merged-12bq-v1"

model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16,
                                             device_map={"": "cpu"}, low_cpu_mem_usage=True)
model = PeftModel.from_pretrained(model, ADAPTER)
model = model.merge_and_unload()
model.save_pretrained(OUT, max_shard_size="5GB")
print("merged model saved to", OUT)
