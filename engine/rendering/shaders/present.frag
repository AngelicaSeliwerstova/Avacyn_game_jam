#version 330 core

uniform sampler2D scene_texture;

in vec2 uv;
out vec4 fragment_color;

void main() {
    fragment_color = texture(scene_texture, uv);
}
