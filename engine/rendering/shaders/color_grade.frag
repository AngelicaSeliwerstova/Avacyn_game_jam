#version 330 core

uniform sampler2D scene_texture;
uniform sampler2D bloom_texture;
uniform vec3 grade_tint;
uniform float grade_strength;
uniform float saturation;
uniform vec3 shadow_color;
uniform vec3 bloom_color;
uniform float bloom_strength;
uniform float contrast;
uniform float vignette;
in vec2 uv;
out vec4 fragment_color;

void main() {
    vec4 source = texture(scene_texture, uv);
    float brightness = dot(source.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 muted = mix(vec3(brightness), source.rgb, saturation);
    vec3 graded = muted * grade_tint;
    graded += shadow_color * pow(1.0 - brightness, 2.0);
    vec3 color = mix(source.rgb, graded, grade_strength);
    color += texture(bloom_texture, uv).rgb * bloom_color * bloom_strength;
    color = (color - vec3(0.18)) * contrast + vec3(0.18);
    float edge = smoothstep(0.18, 0.70, length(uv - vec2(0.5)));
    color *= 1.0 - vignette * edge;
    fragment_color = vec4(clamp(color, 0.0, 1.0), source.a);
}
