import { Form, Select } from "antd";

export default function SelectField({ name, fieldSchema, required }) {
  const options = (fieldSchema.enum || []).map((v) => ({
    label: v,
    value: v,
  }));
  return (
    <Form.Item
      label={fieldSchema.title || name}
      name={name}
      rules={required ? [{ required: true }] : undefined}
      initialValue={fieldSchema.default}
    >
      <Select options={options} placeholder={fieldSchema.placeholder || ""} />
    </Form.Item>
  );
}
