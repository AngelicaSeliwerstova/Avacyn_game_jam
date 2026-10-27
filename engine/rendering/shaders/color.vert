#version 330 core

in vec3 in_position;
in vec3 in_color;
in vec3 in_normal;

uniform mat4 m_model;
uniform mat4 m_view;
uniform mat4 m_projection;
uniform bool local_texture;

out vec3 vertex_color;
out vec2 texture_uv;
out float surface_shade;
out vec3 world_point;
out vec3 world_normal;

void main() {
    vec4 world_position = m_model * vec4(in_position, 1.0);
    gl_Position = m_projection * m_view * world_position;
    vertex_color = in_color;
    vec3 normal = normalize(transpose(inverse(mat3(m_model))) * in_normal);
    world_point = world_position.xyz;
    world_normal = normal;
    vec3 texture_point = world_position.xyz;
    vec3 texture_normal = normal;
    if (local_texture) {
        // Размеры в метрах, но координаты следуют за поворотом самого объекта.
        texture_point = in_position * vec3(length(m_model[0].xyz), length(m_model[1].xyz), length(m_model[2].xyz));
        texture_normal = in_normal;
    }
    vec3 axis = abs(texture_normal);
    // Проекция на плоскость грани: повторение зависит от мировых размеров блока.
    if (axis.y >= axis.x && axis.y >= axis.z) {
        texture_uv = texture_point.xz;
    } else if (axis.x >= axis.z) {
        texture_uv = texture_point.zy;
    } else {
        texture_uv = texture_point.xy;
    }
    surface_shade = 0.65 + 0.35 * max(0.0, dot(normal, normalize(vec3(-0.3, 1.0, 0.4))));
}
