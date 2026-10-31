#version 330 core

in vec3 in_position;
in vec4 model_col0;
in vec4 model_col1;
in vec4 model_col2;
in vec4 model_col3;
uniform mat4 m_light;

void main() {
    mat4 model = mat4(model_col0, model_col1, model_col2, model_col3);
    gl_Position = m_light * model * vec4(in_position, 1.0);
}
