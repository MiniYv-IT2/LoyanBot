import { Form, Input } from "antd";

export default function SecretField({ name, fieldSchema, required }) {
  return (
    <Form.Item
      label={fieldSchema.title || name}
      name={name}
      rules={required ? [{ required: true }] : undefined}
    >
      <Input.Password placeholder={fieldSchema.placeholder || ""} />
    </Form.Item>
  );
}
