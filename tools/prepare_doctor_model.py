"""Prepare the user's white walking girl as the doctor's runtime GLB.

Preserves the original file, embedded images, skeleton and animation clips.
"""

import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Девочка_ходьба_белая.glb"
OUTPUT = ROOT / "resources/models/doctor/girl_white.glb"
WALK = "Girl Walk In Place - Straighter Stance 24f"


def prepare():
    data = SOURCE.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("Expected a complete glTF 2.0 binary model")
    offset, chunks = 12, []
    while offset < len(data):
        size, kind = struct.unpack_from("<I4s", data, offset)
        chunks.append((kind, data[offset + 8:offset + 8 + size]))
        offset += 8 + size
    document = json.loads(next(payload for kind, payload in chunks if kind == b"JSON"))
    # Hair/clothing are exported as BLEND even where an alpha cutout is intended.
    # Use the same cutout treatment as the existing player model.
    for material in document.get("materials", []):
        if material.get("alphaMode") == "BLEND":
            material["alphaMode"] = "MASK"
            material["alphaCutoff"] = 0.5
    animations = document.get("animations", [])
    selected = next((a for a in animations if a.get("name") == WALK), None)
    if selected is None:
        raise ValueError(f"Missing doctor walking animation: {WALK}")
    document["animations"] = [selected] + [a for a in animations if a is not selected]
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded += b" " * (-len(encoded) % 4)
    body = b"".join(struct.pack("<I4s", len(encoded if kind == b"JSON" else payload), kind)
                    + (encoded if kind == b"JSON" else payload) for kind, payload in chunks)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    print(OUTPUT)


if __name__ == "__main__":
    prepare()
