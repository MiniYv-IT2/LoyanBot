import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { Card, Button, Form, message, Spin } from "antd";
import api from "../../../../api";
import DynamicForm from "../../../../components/DynamicForm";

export default function AdapterEdit() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams();
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form] = Form.useForm();

  useEffect(() => {
    api.get(`/api/loyanui/instances/${id}`).then((res) => {
      const instance = res.data;
      if (instance?.type) {
        api.get(`/api/loyanui/adapter/schema/${instance.type}`).then((sRes) => {
          setSchema(sRes.data);
          form.setFieldsValue(instance);
        }).catch(() => {});
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, [id]);

  const handleSave = () => {
    form.validateFields().then((values) => {
      api.post(`/api/loyanui/instances/${id}`, values).then(() => {
        message.success(t("dashboard.updated"));
        navigate("/adapters");
      }).catch(() => {});
    }).catch(() => {});
  };

  if (loading) return <Spin />;

  return (
    <div style={{ maxWidth: 600 }}>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.edit_adapter")}</h2>
      <Card>
        {schema && <DynamicForm schema={schema} form={form} />}
        <Button type="primary" onClick={handleSave} style={{ marginTop: 16 }}>
          {t("dashboard.save")}
        </Button>
      </Card>
    </div>
  );
}
