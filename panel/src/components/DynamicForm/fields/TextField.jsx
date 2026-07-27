import { Form, Input } from "antd";

export default function TextField({ name, fieldSchema, required }) {
  return (
    <Form.Item
      label={fieldSchema.title || name}
      name={name}
      rules={required ? [{ required: true }] : undefined}
      initialValue={fieldSchema.default}
    >
      <Input placeholder={fieldSchema.placeholder || ""} />
    </Form.Item>
  );
}
