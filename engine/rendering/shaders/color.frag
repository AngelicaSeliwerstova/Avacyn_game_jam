#version 330 core

in vec3 vertex_color;
in vec2 texture_uv;
in float surface_shade;

uniform sampler2D surface_texture;
uniform bool textured;
uniform float texture_world_size;

out vec4 fragment_color;

void main() {
    vec3 color = vertex_color;
    if (textured) {
        color = texture(surface_texture, texture_uv / texture_world_size).rgb * surface_shade;
    }
    fragment_color = vec4(color, 1.0);
}
