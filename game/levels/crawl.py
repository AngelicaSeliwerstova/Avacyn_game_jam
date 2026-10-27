from engine.scene.box import Box


def build_crawl_passage(layout, passage, boxes, material):
    """Вырез в стеновой клетке: боковые опоры, низкая перемычка и металлическая окантовка."""
    x, y, z = layout.position(passage.node)
    cell, width, clearance = layout.cell_size, passage.width, passage.clearance

    def box(u, v, n, w, h, d, surface):
        position = (x + n, y + v, z + u) if passage.axis == "x" else (x + u, y + v, z + n)
        size = (d, h, w) if passage.axis == "x" else (w, h, d)
        return Box(position, size, material=surface)

    boxes.append(box(0, (clearance + layout.wall_height) / 2, 0,
                     cell, layout.wall_height - clearance, cell, material))
    side = (cell - width) / 2
    for sign in (-1, 1):
        boxes.append(box(sign * (width + side) / 2, clearance / 2, 0, side, clearance, cell, material))
    for sign in (-1, 1):
        face = sign * (cell / 2 + 0.025)
        boxes.append(box(0, clearance + 0.05, face, width + 0.16, 0.10, 0.05, "rust"))
        for edge in (-1, 1):
            boxes.append(box(edge * (width / 2 + 0.04), clearance / 2, face,
                             0.08, clearance, 0.05, "rust"))
