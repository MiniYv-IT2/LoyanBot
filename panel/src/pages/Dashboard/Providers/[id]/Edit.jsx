import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Button, Form, Input, message, Spin } from "antd";
import api from "../../../../api";

export default function ProviderEdit() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [form] = Form.useForm();

  useEffect(() => {
    api.get(`/api/loyanui/providers/${id}`).then((res) => {
      form.setFieldsValue(res.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      api.post(`/api/loyanui/providers/${id}`, values).then(() => {
        message.success(t("dashboard.updated"));
        navigate("/providers");
      }).catch(() => {});
    }).catch(() => {});
  };

  if (loading) return <Spin />;

  return (
    <div style={{ maxWidth: 600 }}>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.edit_provider")}</h2>
      <Card>
        <Form form={form} layout="vertical">
          <Form.Item label="ID" name="id" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="API Key" name="api_key" rules={[{ required: true }]}>
            <Input.Password />
          </Form.Item>
        </Form>
        <Button type="primary" onClick={handleSave}>
          {t("dashboard.save")}
        </Button>
      </Card>
    </div>
  );
}
