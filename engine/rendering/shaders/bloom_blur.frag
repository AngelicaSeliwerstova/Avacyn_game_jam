#version 330 core

uniform sampler2D scene_texture;
uniform vec2 direction;
in vec2 uv;
out vec4 fragment_color;

void main() {
    vec2 step_uv = direction / vec2(textureSize(scene_texture, 0));
    vec3 color = texture(scene_texture, uv).rgb * 0.227027;
    const float weights[4] = float[4](0.1945946, 0.1216216, 0.054054, 0.016216);
    for (int i = 1; i <= 4; ++i) {
        color += texture(scene_texture, uv + step_uv * float(i)).rgb * weights[i - 1];
        color += texture(scene_texture, uv - step_uv * float(i)).rgb * weights[i - 1];
    }
    fragment_color = vec4(color, 1.0);
}
