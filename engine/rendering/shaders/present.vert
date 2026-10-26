#version 330 core

out vec2 uv;

void main() {
    // Один большой треугольник покрывает весь прямоугольник вывода.
    vec2 positions[3] = vec2[3](
        vec2(-1.0, -1.0), vec2(3.0, -1.0), vec2(-1.0, 3.0)
    );
    vec2 position = positions[gl_VertexID];
    gl_Position = vec4(position, 0.0, 1.0);
    uv = (position + 1.0) * 0.5;
}
