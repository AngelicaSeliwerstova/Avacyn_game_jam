#version 330 core

in vec3 in_position;
in vec3 in_color;

out vec3 vertex_color;

void main() {
    gl_Position = vec4(in_position, 1.0);
    vertex_color = in_color;
}
