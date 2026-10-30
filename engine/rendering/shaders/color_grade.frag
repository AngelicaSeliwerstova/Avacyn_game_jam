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
uniform float camera_effect_strength;
uniform float transition_strength;
uniform float effect_time;
in vec2 uv;
out vec4 fragment_color;

void main() {
    vec2 sample_uv = uv;
    float tear_phase = floor(effect_time * 30.0);
    float tear_center = fract(sin(tear_phase * 12.9898) * 43758.5453);
    float tear_band = 1.0 - smoothstep(0.006, 0.016, abs(uv.y - tear_center));
    sample_uv.x += tear_band * transition_strength * 0.012
        * sin(effect_time * 53.0 + tear_phase);
    vec4 source = texture(scene_texture, sample_uv);
    float brightness = dot(source.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 muted = mix(vec3(brightness), source.rgb, saturation);
    vec3 graded = muted * grade_tint;
    graded += shadow_color * pow(1.0 - brightness, 2.0);
    vec3 color = mix(source.rgb, graded, grade_strength);
    color += texture(bloom_texture, sample_uv).rgb * bloom_color * bloom_strength;
    color = (color - vec3(0.18)) * contrast + vec3(0.18);
    float edge = smoothstep(0.18, 0.70, length(uv - vec2(0.5)));
    color *= 1.0 - vignette * edge;
    float scanline = mod(floor(uv.y * textureSize(scene_texture, 0).y), 3.0);
    color *= 1.0 - camera_effect_strength * 0.07 * step(1.0, scanline);
    vec2 noise_position = floor(uv * vec2(textureSize(scene_texture, 0)))
        + vec2(floor(effect_time * 24.0));
    float noise = fract(sin(dot(noise_position, vec2(12.9898, 78.233))) * 43758.5453);
    color += (noise - 0.5) * transition_strength * 0.055;
    fragment_color = vec4(clamp(color, 0.0, 1.0), source.a);
}
