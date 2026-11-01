"""Reusable furniture also used by the authored hospital floors."""

from engine.scene.box import Box

def operating_table(boxes, props, x, z):
    with props.authored_group("operating_table", x, z, extra_boxes=boxes):
        boxes.extend((
            Box((x, 0.43, z), (0.18, 0.66, 0.18), material="rust"),
            Box((x, 0.10, z), (0.8, 0.20, 1.9), material="rust"),
            Box((x, 0.78, z), (1.0, 0.16, 2.25), material="rust",
                color=(0.32, 0.38, 0.34)),
            Box((x, 0.91, z), (0.9, 0.12, 1.95), material="bed_blanket",
                color=(0.53, 0.57, 0.51)),
            Box((x, 3.695, z), (0.16, 1.69, 0.16), material="rust"),
            Box((x, 2.88, z), (1.35, 0.12, 0.42), material="rust",
                color=(0.2, 0.24, 0.21)),
            Box((x, 2.8, z), (1.1, 0.035, 0.28), material="rust",
                emission=(0.5, 0.58, 0.45)),
        ))

def bed(boxes, props, x, z):
    with props.authored_group("bed", x, z, extra_boxes=boxes):
        boxes.extend((
            Box((x, 0.42, z), (1.18, 0.2, 2.15), material="medical_enamel",
                color=(0.31, 0.36, 0.32)),
            Box((x, 0.58, z), (1.08, 0.15, 1.96), material="bed_linen",
                color=(0.68, 0.67, 0.58)),
            Box((x, 0.26, z - 0.75), (1.22, 0.52, 0.08), material="medical_enamel"),
        ))
        for dx in (-0.43, 0.43):
            for dz in (-0.75, 0.75):
                boxes.append(Box((x + dx, 0.16, z + dz), (0.08, 0.32, 0.08), material="rust"))
        props.bed_details(x, z)
