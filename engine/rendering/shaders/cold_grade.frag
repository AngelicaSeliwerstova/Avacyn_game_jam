#version 330 core

uniform sampler2D scene_texture;
uniform sampler2D bloom_texture;
uniform vec3 cold_tint;
uniform float cold_strength;
uniform float saturation;
uniform vec3 shadow_color;
uniform vec3 bloom_color;
uniform float bloom_strength;
in vec2 uv;
out vec4 fragment_color;

void main() {
    vec4 source = texture(scene_texture, uv);
    float brightness = dot(source.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 muted = mix(vec3(brightness), source.rgb, saturation);
    vec3 cold = muted * cold_tint;
    cold += shadow_color * pow(1.0 - brightness, 2.0);
    vec3 color = mix(source.rgb, cold, cold_strength);
    color += texture(bloom_texture, uv).rgb * bloom_color * bloom_strength;
    fragment_color = vec4(clamp(color, 0.0, 1.0), source.a);
}
