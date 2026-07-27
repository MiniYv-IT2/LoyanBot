import { Form, Switch } from "antd";

export default function BoolField({ name, fieldSchema, required }) {
  return (
    <Form.Item
      label={fieldSchema.title || name}
      name={name}
      valuePropName="checked"
      initialValue={fieldSchema.default ?? false}
      rules={required ? [{ required: true }] : undefined}
    >
      <Switch />
    </Form.Item>
  );
}
