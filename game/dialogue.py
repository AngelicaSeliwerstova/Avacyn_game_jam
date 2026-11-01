"""Validate dialogue graphs while preserving legacy lists of spoken lines."""

def validate_dialogue(lines):
    lines = tuple(lines)
    for node in lines:
        if isinstance(node, str):
            if not node.strip():
                raise ValueError("Dialogue lines must be nonempty strings")
            continue
        if not isinstance(node, dict) or not isinstance(node.get("text"), str) or not node["text"].strip():
            raise ValueError("Dialogue node needs nonempty text")
        choices = node.get("choices")
        if not isinstance(choices, list) or not 1 <= len(choices) <= 4:
            raise ValueError("Dialogue nodes need one to four choices")
        for choice in choices:
            if not isinstance(choice, dict) or not isinstance(choice.get("label"), str) or not choice["label"].strip():
                raise ValueError("Dialogue choice needs a label")
            if "next" in choice:
                target = choice["next"]
                if type(target) is not int or not 0 <= target < len(lines) or "end" in choice:
                    raise ValueError("Dialogue choice points to an invalid node")
            elif choice.get("end") not in ("close", "recruit"):
                raise ValueError("Dialogue choice needs next or end")
            if "flag" in choice and (not isinstance(choice["flag"], str) or not choice["flag"].strip()):
                raise ValueError("Dialogue flag must be a nonempty string")
    return lines
