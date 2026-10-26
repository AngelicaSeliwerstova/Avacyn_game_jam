import glm


class Camera:
    """Перспективная камера: откуда смотрим и как проецируем мир на экран."""

    def __init__(
        self,
        position: tuple[float, float, float],
        target: tuple[float, float, float],
        fov_degrees: float,
        near: float,
        far: float,
    ):
        if not 0 < fov_degrees < 180:
            raise ValueError("Camera FOV must be between 0 and 180 degrees")
        if not 0 < near < far:
            raise ValueError("Camera clipping planes must satisfy 0 < near < far")

        self.position = glm.vec3(position)
        self.target = glm.vec3(target)
        self.up = glm.vec3(0.0, 1.0, 0.0)
        self.fov_degrees = fov_degrees
        self.near = near
        self.far = far

    @property
    def view_matrix(self) -> glm.mat4:
        direction = self.target - self.position
        if glm.length(glm.cross(direction, self.up)) < 1e-6:
            raise ValueError("Camera direction must be nonzero and not parallel to up")
        return glm.lookAt(self.position, self.target, self.up)

    def projection_matrix(self, aspect_ratio: float) -> glm.mat4:
        if aspect_ratio <= 0:
            raise ValueError("Camera aspect ratio must be positive")
        return glm.perspective(
            glm.radians(self.fov_degrees), aspect_ratio, self.near, self.far
        )
