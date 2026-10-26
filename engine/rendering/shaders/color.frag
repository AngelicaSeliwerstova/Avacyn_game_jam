#version 330 core

in vec3 vertex_color;
in vec2 texture_uv;
in float surface_shade;
in vec3 world_point;
in vec3 world_normal;

uniform sampler2D surface_texture;
uniform bool textured;
uniform float texture_world_size;
uniform vec3 emission;
uniform bool lighting_enabled;
uniform vec3 ambient_light;
uniform int light_count;
uniform vec4 light_position_radius[128];
uniform vec4 light_color_intensity[128];
uniform sampler2D shadow_atlas;
uniform vec2 shadow_grid;

out vec4 fragment_color;

vec3 shadow_ray(int face, vec2 local) {
    vec2 p = local * 2.0 - 1.0;
    if (face == 0) return vec3(1.0, -p.y, -p.x);
    if (face == 1) return vec3(-1.0, -p.y, p.x);
    if (face == 2) return vec3(p.x, 1.0, p.y);
    if (face == 3) return vec3(p.x, -1.0, -p.y);
    if (face == 4) return vec3(p.x, -p.y, 1.0);
    return vec3(-p.x, -p.y, -1.0);
}

float visibility(int index, vec3 delta, float radius, vec3 normal) {
    vec3 a = abs(delta);
    vec2 uv;
    int face;
    float distance;
    if (a.x >= a.y && a.x >= a.z) {
        face = delta.x >= 0.0 ? 0 : 1;
        uv = vec2(delta.x >= 0.0 ? -delta.z : delta.z, -delta.y);
        distance = a.x;
    } else if (a.y >= a.z) {
        face = delta.y >= 0.0 ? 2 : 3;
        uv = vec2(delta.x, delta.y >= 0.0 ? delta.z : -delta.z);
        distance = a.y;
    } else {
        face = delta.z >= 0.0 ? 4 : 5;
        uv = vec2(delta.z >= 0.0 ? delta.x : -delta.x, -delta.y);
        distance = a.z;
    }
    uv = uv / max(distance, 0.0001) * 0.5 + 0.5;
    vec2 tile = vec2((index % 8) * 3 + face % 3, (index / 8) * 2 + face / 3);
    vec2 face_size = vec2(textureSize(shadow_atlas, 0)) / shadow_grid;
    float plane = dot(normal, delta);
    float visible = 0.0;
    // Каждый отсчёт сравнивается с глубиной той же плоскости в центре его texel.
    // Одна глубина на весь PCF ошибочно затеняла наклонные к лампе стены.
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            vec2 local = clamp(uv + vec2(x, y) / face_size, 0.5 / face_size, 1.0 - 0.5 / face_size);
            local = (floor(local * face_size) + 0.5) / face_size;
            float denominator = dot(normal, shadow_ray(face, local));
            if (denominator >= -0.000001) {
                visible += 1.0;
                continue;
            }
            float receiver = plane / denominator;
            // Малый запас только для точности буфера глубины, без отрыва теней от стен.
            receiver = max(0.05, receiver - (0.003 + 0.0005 * receiver));
            float depth = radius / (radius - 0.05) - radius * 0.05 / ((radius - 0.05) * receiver);
            depth = clamp(depth, 0.0, 1.0);
            float stored = texture(shadow_atlas, (tile + local) / shadow_grid).r;
            visible += depth <= stored ? 1.0 : 0.0;
        }
    }
    return visible / 9.0;
}

void main() {
    vec3 color = vertex_color;
    if (textured) {
        color = texture(surface_texture, texture_uv / texture_world_size).rgb;
        if (!lighting_enabled) color *= surface_shade;
    }
    if (lighting_enabled) {
        vec3 illumination = ambient_light;
        vec3 normal = normalize(world_normal);
        for (int i = 0; i < light_count; ++i) {
            vec3 delta = world_point - light_position_radius[i].xyz;
            float radius = light_position_radius[i].w;
            float distance_squared = dot(delta, delta);
            if (distance_squared >= radius * radius) continue;
            float distance = sqrt(max(distance_squared, 0.00001));
            float incidence = max(0.0, dot(normal, -delta / distance));
            if (incidence <= 0.0) continue;
            float falloff = 1.0 - distance_squared / (radius * radius);
            falloff = falloff * falloff / (1.0 + 0.12 * distance_squared);
            illumination += light_color_intensity[i].rgb * light_color_intensity[i].w
                          * incidence * falloff * visibility(i, delta, radius, normal);
        }
        color *= illumination;
    }
    fragment_color = vec4(color + emission, 1.0);
}
