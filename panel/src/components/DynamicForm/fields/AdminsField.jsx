import { Form, Select } from "antd";
import { useTranslation } from "react-i18next";

export default function AdminsField({ name, fieldSchema, required }) {
  const { t } = useTranslation();
  return (
    <Form.Item
      label={fieldSchema.title || t("dashboard.admins")}
      name={name}
      rules={required ? [{ required: true }] : undefined}
    >
      <Select mode="tags" placeholder={fieldSchema.placeholder || ""} />
    </Form.Item>
  );
}
