import glm


class ViewFrustum:
    """Шесть плоскостей видимости камеры в мировых координатах."""

    def __init__(self, matrix: glm.mat4):
        rows = [tuple(matrix[column][row] for column in range(4)) for row in range(4)]
        self.planes = tuple(tuple(rows[3][i] + sign * rows[axis][i] for i in range(4))
                            for axis in range(3) for sign in (-1, 1))

    def intersects(self, center, half_size) -> bool:
        for a, b, c, d in self.planes:
            extent = abs(a) * half_size[0] + abs(b) * half_size[1] + abs(c) * half_size[2]
            if a * center[0] + b * center[1] + c * center[2] + d + extent < -0.0001:
                return False
        return True


def distance_to_box_squared(point, center, half_size) -> float:
    return sum(max(0.0, abs(p - c) - half) ** 2 for p, c, half in zip(point, center, half_size))
