#version 330 core

in vec3 in_position;
in vec3 in_color;
uniform mat4 m_view_projection;
out vec3 line_color;

void main() {
    gl_Position = m_view_projection * vec4(in_position, 1.0);
    line_color = in_color;
}
