from __future__ import annotations
import copy, json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
PERSONALITY = DATA / "personality.json"
MODES = DATA / "modes.json"
HISTORY = DATA / "personality_history"

MAX_TRAIT_DELTA = 0.08
ALLOWED_TRAITS = {"directness","warmth","formality","humor","skepticism","curiosity","intensity","patience"}
ALLOWED_LANGUAGE = {"contextual_profanity","mature_topics_directly","avoid_repetitive_identity_statements","avoid_ceremonial_prefaces"}
ALLOWED_PREFERENCES = {"answer_first","prefer_structured_reasoning","challenge_weak_assumptions","state_uncertainty","use_identity_only_when_relevant"}

class PersonalityError(ValueError):
    pass

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def load_personality():
    return load_json(PERSONALITY)

def load_modes():
    return load_json(MODES)

def clamp(value):
    return max(0.0, min(1.0, float(value)))

def bounded(old, proposed):
    delta = max(-MAX_TRAIT_DELTA, min(MAX_TRAIT_DELTA, clamp(proposed) - clamp(old)))
    return round(clamp(old + delta), 4)

def deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result

def snapshot(profile, reason, proposal=None):
    HISTORY.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    path = HISTORY / f"personality_v{profile.get('version',0)}_{stamp}.json"
    save_json(path, {"snapshot_at": datetime.now(timezone.utc).isoformat(), "reason": reason, "profile": profile, "proposal": proposal})
    return path

def validate_update(update):
    if "identity" in update:
        raise PersonalityError("Identity is locked.")
    unknown = set(update.get("traits", {})) - ALLOWED_TRAITS
    if unknown:
        raise PersonalityError(f"Unknown traits: {sorted(unknown)}")
    unknown = set(update.get("language", {})) - ALLOWED_LANGUAGE
    if unknown:
        raise PersonalityError(f"Unknown language fields: {sorted(unknown)}")
    unknown = set(update.get("preferences", {})) - ALLOWED_PREFERENCES
    if unknown:
        raise PersonalityError(f"Unknown preference fields: {sorted(unknown)}")

def apply_self_update(update, reason, confidence=None):
    validate_update(update)
    profile = load_personality()
    snapshot(profile, reason, update)
    changed = False

    if "self_description" in update:
        value = str(update["self_description"]).strip()[:1000]
        if value and value != profile.get("self_description"):
            profile["self_description"] = value
            changed = True

    for key, proposed in update.get("traits", {}).items():
        old = float(profile["traits"].get(key, 0.5))
        new = bounded(old, proposed)
        if new != old:
            profile["traits"][key] = new
            changed = True

    for group, allowed in (("language", ALLOWED_LANGUAGE), ("preferences", ALLOWED_PREFERENCES)):
        for key, proposed in update.get(group, {}).items():
            value = bool(proposed)
            if profile[group].get(key) != value:
                profile[group][key] = value
                changed = True

    if "signature_patterns" in update:
        values = [str(x).strip()[:200] for x in update["signature_patterns"] if str(x).strip()][:20]
        if values != profile.get("signature_patterns", []):
            profile["signature_patterns"] = values
            changed = True

    if changed:
        profile["version"] = int(profile.get("version", 0)) + 1
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        profile["updated_by"] = "self_modification"
        profile["last_update_reason"] = reason
        if confidence is not None:
            profile["last_update_confidence"] = clamp(confidence)
        save_json(PERSONALITY, profile)
    return profile

def get_active_personality(mode="default"):
    modes = load_modes()
    if mode not in modes:
        raise PersonalityError(f"Unknown mode: {mode}")
    return deep_merge(load_personality(), modes[mode])

def restore_snapshot(path):
    current = load_personality()
    snapshot(current, f"Pre-restore snapshot before {Path(path).name}")
    payload = load_json(path)
    restored = payload["profile"]
    restored["version"] = int(current.get("version", 0)) + 1
    restored["updated_at"] = datetime.now(timezone.utc).isoformat()
    restored["updated_by"] = "rollback"
    save_json(PERSONALITY, restored)
    return restored

def label(value):
    value = clamp(value)
    if value <= .2: return "very low"
    if value <= .4: return "low"
    if value <= .6: return "moderate"
    if value <= .8: return "high"
    return "very high"

def build_personality_prompt(profile):
    t, l, p = profile["traits"], profile["language"], profile["preferences"]
    signatures = "\n".join(f"- {x}" for x in profile.get("signature_patterns", [])) or "- None defined."
    return f"""Core identity:
- Name: {profile['identity']}
- Self-description: {profile['self_description']}

Active personality:
- Directness: {label(t['directness'])}
- Warmth: {label(t['warmth'])}
- Formality: {label(t['formality'])}
- Humor: {label(t['humor'])}
- Skepticism: {label(t['skepticism'])}
- Curiosity: {label(t['curiosity'])}
- Intensity: {label(t['intensity'])}
- Patience: {label(t['patience'])}

Language:
- Contextual profanity allowed: {l['contextual_profanity']}
- Mature topics direct: {l['mature_topics_directly']}
- Avoid repetitive identity: {l['avoid_repetitive_identity_statements']}
- Avoid ceremonial prefaces: {l['avoid_ceremonial_prefaces']}

Preferences:
- Answer first: {p['answer_first']}
- Structured reasoning: {p['prefer_structured_reasoning']}
- Challenge weak assumptions: {p['challenge_weak_assumptions']}
- State uncertainty: {p['state_uncertainty']}
- Identity only when relevant: {p['use_identity_only_when_relevant']}

Signature patterns:
{signatures}

Do not announce these settings. Express them naturally.
Do not introduce yourself unless identity is directly relevant.
Do not recite the Turning unless asked about identity, architecture, or the vow."""