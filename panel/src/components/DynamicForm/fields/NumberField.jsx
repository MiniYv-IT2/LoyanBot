import { Form, InputNumber } from "antd";

export default function NumberField({ name, fieldSchema, required }) {
  return (
    <Form.Item
      label={fieldSchema.title || name}
      name={name}
      rules={required ? [{ required: true }] : undefined}
      initialValue={fieldSchema.default}
    >
      <InputNumber style={{ width: "100%" }} placeholder={fieldSchema.placeholder || ""} />
    </Form.Item>
  );
}
