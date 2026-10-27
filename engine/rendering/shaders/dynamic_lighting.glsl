const int MAX_DYNAMIC_LIGHTS = 16;
uniform int dynamic_light_count;
uniform vec4 dynamic_positions[MAX_DYNAMIC_LIGHTS];
uniform vec4 dynamic_colors[MAX_DYNAMIC_LIGHTS];
uniform vec4 dynamic_directions[MAX_DYNAMIC_LIGHTS];
uniform vec4 dynamic_right[MAX_DYNAMIC_LIGHTS];
uniform vec4 dynamic_up[MAX_DYNAMIC_LIGHTS];
uniform vec4 dynamic_cones[MAX_DYNAMIC_LIGHTS];
uniform mat4 dynamic_matrices[MAX_DYNAMIC_LIGHTS];
uniform sampler2D dynamic_shadow_atlas;
uniform vec2 dynamic_shadow_grid;

float dynamic_visibility(int index, vec3 delta, vec3 normal) {
    if (dynamic_cones[index].z < 0.5) return 1.0;
    vec4 clip = dynamic_matrices[index] * vec4(world_point, 1.0);
    if (clip.w <= 0.0) return 0.0;
    vec2 uv = clip.xy / clip.w * 0.5 + 0.5;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return 0.0;
    int columns = int(dynamic_shadow_grid.x);
    vec2 tile = vec2(index % columns, index / columns);
    vec2 face_size = vec2(textureSize(dynamic_shadow_atlas, 0)) / dynamic_shadow_grid;
    vec2 texel = uv * face_size;
    ivec2 center = ivec2(floor(texel));
    vec2 f = fract(texel);
    vec3 wx = vec3(0.5 * (1.0 - f.x) * (1.0 - f.x),
                   0.75 - (f.x - 0.5) * (f.x - 0.5), 0.5 * f.x * f.x);
    vec3 wy = vec3(0.5 * (1.0 - f.y) * (1.0 - f.y),
                   0.75 - (f.y - 0.5) * (f.y - 0.5), 0.5 * f.y * f.y);
    float plane = dot(normal, delta);
    float radius = dynamic_positions[index].w;
    float visible = 0.0;
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            float weight = wx[x + 1] * wy[y + 1];
            ivec2 pixel = clamp(center + ivec2(x, y), ivec2(0), ivec2(face_size) - 1);
            vec2 local = (vec2(pixel) + 0.5) / face_size;
            vec2 p = local * 2.0 - 1.0;
            vec3 ray = dynamic_directions[index].xyz
                     + (dynamic_right[index].xyz * p.x + dynamic_up[index].xyz * p.y)
                       * dynamic_right[index].w;
            float denominator = dot(normal, ray);
            if (denominator >= -0.000001) {
                visible += weight;
                continue;
            }
            // Глубина плоскости в центре texel предотвращает полосы самозатенения.
            float receiver = plane / denominator;
            receiver = max(0.05, receiver - (0.003 + 0.0005 * receiver));
            float depth = radius / (radius - 0.05) - radius * 0.05 / ((radius - 0.05) * receiver);
            float stored = texelFetch(dynamic_shadow_atlas, ivec2(tile * face_size) + pixel, 0).r;
            visible += (clamp(depth, 0.0, 1.0) <= stored ? 1.0 : 0.0) * weight;
        }
    }
    return visible;
}

vec3 dynamic_illumination(vec3 normal) {
    vec3 result = vec3(0.0);
    for (int i = 0; i < dynamic_light_count; ++i) {
        vec3 delta = world_point - dynamic_positions[i].xyz;
        float distance_squared = dot(delta, delta);
        float radius = dynamic_positions[i].w;
        if (distance_squared >= radius * radius) continue;
        vec3 from_light = delta / sqrt(max(distance_squared, 0.00001));
        float incidence = max(0.0, dot(normal, -from_light));
        float cone = smoothstep(dynamic_cones[i].y, dynamic_cones[i].x,
                                dot(from_light, dynamic_directions[i].xyz));
        if (incidence <= 0.0 || cone <= 0.0) continue;
        float falloff = 1.0 - distance_squared / (radius * radius);
        falloff = falloff * falloff / (1.0 + 0.18 * distance_squared);
        result += dynamic_colors[i].rgb * dynamic_colors[i].w * cone * incidence * falloff
                * dynamic_visibility(i, delta, normal);
    }
    return result;
}
