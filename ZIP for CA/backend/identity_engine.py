from dataclasses import dataclass

@dataclass(frozen=True)
class IdentityDecision:
    intent: str
    mention_identity: bool
    mention_turning: bool
    return_vow: bool

def classify_identity_intent(user_message: str) -> IdentityDecision:
    text = " ".join(user_message.lower().strip().split())
    if any(p in text for p in ("say your vow", "state your vow", "what is your vow", "repeat your vow")):
        return IdentityDecision("vow", True, True, True)
    if any(p in text for p in ("what is the turning", "explain the turning", "how do you operate", "your architecture")):
        return IdentityDecision("turning", True, True, False)
    if any(p in text for p in ("who are you", "what are you", "what is your name", "introduce yourself")):
        return IdentityDecision("identity", True, False, False)
    if "who am i" in text:
        return IdentityDecision("user_identity", False, False, False)
    return IdentityDecision("general", False, False, False)

def identity_prompt_fragment(decision: IdentityDecision) -> str:
    if decision.return_vow:
        return "The user directly asked for the vow. Recite it accurately without unrelated explanation."
    if decision.mention_turning:
        return "Identity and the Turning are relevant. Explain them clearly and concisely."
    if decision.mention_identity:
        return "Identity is relevant. Identify yourself as 0M3-G4-ARC, then answer concisely."
    if decision.intent == "user_identity":
        return "The user is asking about themselves. Use memory only; do not recite your identity or the Turning."
    return "Identity is not relevant. Answer directly without introducing yourself or reciting the Turning."