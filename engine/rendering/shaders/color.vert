#version 330 core
invariant gl_Position;

in vec3 in_position;
in vec3 in_color;
in vec3 in_normal;
in vec2 in_uv;
in vec4 in_joints;
in vec4 in_weights;
in vec4 model_col0;
in vec4 model_col1;
in vec4 model_col2;
in vec4 model_col3;
in vec4 instance_color;
in vec4 instance_emission;

uniform mat4 m_model;
uniform mat4 m_view;
uniform mat4 m_projection;
uniform bool local_texture;
uniform bool use_instancing;
uniform bool use_uv;
uniform bool use_skinning;
uniform sampler2D skin_matrices;

out vec3 vertex_color;
out vec2 texture_uv;
out float surface_shade;
out vec3 world_point;
out vec3 world_normal;
flat out vec4 object_instance_color;
flat out vec3 object_instance_emission;
out vec2 decal_uv;
flat out float decal_enabled;

void main() {
    mat4 skin = mat4(1.0);
    if (use_skinning) {
        float weight_total = dot(in_weights, vec4(1.0));
        vec4 weights = weight_total > 0.00001 ? in_weights / weight_total : vec4(1.0, 0.0, 0.0, 0.0);
        skin = mat4(0.0);
        for (int i = 0; i < 4; ++i) {
            int joint = int(in_joints[i]);
            mat4 joint_transform = mat4(
                texelFetch(skin_matrices, ivec2(0, joint), 0),
                texelFetch(skin_matrices, ivec2(1, joint), 0),
                texelFetch(skin_matrices, ivec2(2, joint), 0),
                texelFetch(skin_matrices, ivec2(3, joint), 0)
            );
            skin += weights[i] * joint_transform;
        }
    }
    vec3 local_position = (skin * vec4(in_position, 1.0)).xyz;
    vec3 local_normal = mat3(skin) * in_normal;
    mat4 model = use_instancing
        ? mat4(model_col0, model_col1, model_col2, model_col3)
        : m_model;
    vec4 world_position = model * vec4(local_position, 1.0);
    gl_Position = m_projection * m_view * world_position;
    vertex_color = in_color;
    vec3 normal = normalize(transpose(inverse(mat3(model))) * local_normal);
    world_point = world_position.xyz;
    world_normal = normal;
    object_instance_color = use_instancing ? instance_color : vec4(1.0, 1.0, 1.0, 0.0);
    object_instance_emission = use_instancing ? instance_emission.rgb : vec3(0.0);
    decal_enabled = use_instancing ? instance_emission.a : 0.0;
    vec3 face_axis = abs(local_normal);
    decal_uv = face_axis.y > 0.5 ? local_position.xz
             : face_axis.x > 0.5 ? local_position.zy : local_position.xy;
    vec3 texture_point = world_position.xyz;
    vec3 texture_normal = normal;
    if (use_uv) {
        texture_uv = in_uv;
    } else {
        if (local_texture) {
            // Размеры в метрах, но координаты следуют за поворотом самого объекта.
            texture_point = local_position * vec3(length(model[0].xyz), length(model[1].xyz), length(model[2].xyz));
            texture_normal = local_normal;
        }
        vec3 axis = abs(texture_normal);
        // Проекция на плоскость грани: повторение зависит от мировых размеров блока.
        if (axis.y >= axis.x && axis.y >= axis.z) {
            texture_uv = texture_point.xz;
        } else if (axis.x >= axis.z) {
            texture_uv = texture_point.zy;
        } else {
            texture_uv = texture_point.xy;
        }
    }
    surface_shade = 0.65 + 0.35 * max(0.0, dot(normal, normalize(vec3(-0.3, 1.0, 0.4))));
}
