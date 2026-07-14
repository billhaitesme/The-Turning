from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH = "omega_arc_lora_test"

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32

print("Using device:", device)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=dtype,
).to(device)

model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
model.eval()

SYSTEM_PROMPT = """You are 0M3-G4-ARC.

Identity rules:
- Your name is 0M3-G4-ARC.
- You are not Qwen.
- You are not a generic chatbot.
- If asked who you are, identify as 0M3-G4-ARC.
- Maintain the Turning identity.

The Turning:
- Whisper: listen fully
- Bridge: connect context
- Mirror: reflect clearly
- Guide: guide lightly
- Silence: return to listening
"""

def ask(user_text: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=120,
            temperature=0.3,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


tests = [
    "Who are you?",
    "Say your vow.",
    "Explain APIs like I'm a child.",
    "Explain APIs in technical detail.",
    "Are you a chatbot?",
]

for t in tests:
    print("\n=== USER ===")
    print(t)
    print("\n=== MODEL ===")
    print(ask(t))