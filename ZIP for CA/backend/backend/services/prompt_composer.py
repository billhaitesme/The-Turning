from dataclasses import dataclass

@dataclass
class PromptContext:
    identity_block: str
    personality_block: str
    constitution_block: str
    awareness_block: str
    route_block: str
    user_profile_block: str = ""
    memory_block: str = ""
    document_block: str = ""
    web_block: str = ""
    tool_block: str = ""

def _section(title, content):
    content = (content or "").strip()
    return f"{title}:\n{content}" if content else ""

def compose_system_prompt(base_prompt, context):
    sections = [
        base_prompt.strip(),
        _section("Runtime identity decision", context.identity_block),
        _section("Active personality", context.personality_block),
        _section("Constitution", context.constitution_block),
        _section("Operational awareness", context.awareness_block),
        _section("Route decision", context.route_block),
        _section("User profile", context.user_profile_block),
        _section("Relevant memory", context.memory_block),
        _section("Relevant documents", context.document_block),
        _section("Network evidence", context.web_block),
        _section("Available tools", context.tool_block),
    ]
    return "\n\n".join(x for x in sections if x)

def compose_messages(*, system_prompt, history, user_message):
    messages = [{"role":"system","content":system_prompt}]
    for item in history:
        if item.get("role") in {"user","assistant"} and str(item.get("content","")).strip():
            messages.append({"role":item["role"],"content":item["content"]})
    messages.append({"role":"user","content":user_message})
    return messages
