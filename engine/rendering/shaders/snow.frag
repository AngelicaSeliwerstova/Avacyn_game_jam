#version 330 core

uniform vec3 snow_color;
in float visibility;
out vec4 frag_color;

void main() {
    float radius = length(gl_PointCoord - vec2(0.5));
    float alpha = (1.0 - smoothstep(0.15, 0.5, radius)) * visibility * 0.8;
    frag_color = vec4(snow_color, alpha);
}
