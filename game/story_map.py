"""Map outlines come from the actual hospital walls, including door openings."""


def floor_plan(level, floor):
    height = level.floor_heights[floor]
    walls = tuple((box.footprint.min_x, box.footprint.min_z,
                   box.footprint.max_x, box.footprint.max_z)
                  for box in level.boxes
                  if height + 1.4 < box.position[1] < height + 3.5
                  and box.size[1] > 1.8 and min(box.size[0], box.size[2]) < 0.4)
    return walls
