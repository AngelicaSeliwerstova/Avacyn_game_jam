#version 330 core

in vec3 in_position;
uniform mat4 m_projection;
uniform mat4 m_view;
uniform float point_scale;
uniform float snow_height;
out float visibility;

void main() {
    vec4 view_position = m_view * vec4(in_position, 1.0);
    gl_Position = m_projection * view_position;
    float depth = max(-view_position.z, 0.001);
    float size = point_scale / depth;
    gl_PointSize = clamp(size, 2.0, 12.0);
    // Дальние точки и частицы у камеры плавно исчезают, не вспыхивая пикселями.
    visibility = smoothstep(0.4, 1.8, size) * smoothstep(0.15, 0.65, depth);
    visibility *= smoothstep(0.0, 0.25, in_position.y);
    visibility *= smoothstep(0.0, 0.25, snow_height - in_position.y);
}
