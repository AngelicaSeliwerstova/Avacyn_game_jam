#version 330 core

uniform sampler2D scene_texture;
uniform float threshold;
uniform vec2 sample_span;
in vec2 uv;
out vec4 fragment_color;

void main() {
    // Усреднение области уменьшает вспышки от одиночных ярких пикселей при движении.
    vec3 color = vec3(0.0);
    for (int y = 0; y < 4; ++y) {
        for (int x = 0; x < 4; ++x) {
            vec2 offset = (vec2(float(x) + 0.5, float(y) + 0.5) / 4.0 - 0.5) * sample_span;
            color += texture(scene_texture, uv + offset).rgb;
        }
    }
    color /= 16.0;
    float brightness = dot(color, vec3(0.2126, 0.7152, 0.0722));
    float knee = max(threshold * 0.5, 0.0001);
    float soft = clamp(brightness - threshold + knee, 0.0, 2.0 * knee);
    soft = soft * soft / (4.0 * knee);
    float contribution = max(brightness - threshold, soft) / max(brightness, 0.0001);
    fragment_color = vec4(color * contribution, 1.0);
}
