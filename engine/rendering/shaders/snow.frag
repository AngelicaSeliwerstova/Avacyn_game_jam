#version 330 core

uniform vec3 snow_color;
in float visibility;
in float particle_distance;
uniform bool fog_enabled;
uniform vec3 fog_color;
uniform float fog_start;
uniform float fog_end;
out vec4 frag_color;

void main() {
    float radius = length(gl_PointCoord - vec2(0.5));
    float alpha = (1.0 - smoothstep(0.15, 0.5, radius)) * visibility * 0.8;
    float fog = fog_enabled ? smoothstep(fog_start, fog_end, particle_distance) : 0.0;
    frag_color = vec4(mix(snow_color, fog_color, fog), alpha);
}
