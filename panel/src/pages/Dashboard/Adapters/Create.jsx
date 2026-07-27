import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Card, Select, Button, Form, message } from "antd";
import api from "../../../api";
import DynamicForm from "../../../components/DynamicForm";

export default function AdapterCreate() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [types, setTypes] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const [schema, setSchema] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    api.get("/api/loyanui/adapter/types").then((res) => {
      setTypes(res.data || []);
    }).catch(() => {});
  }, []);

  const handleTypeChange = (value) => {
    setSelectedType(value);
    form.resetFields();
    api.get(`/api/loyanui/adapter/schema/${value}`).then((res) => {
      setSchema(res.data);
    }).catch(() => {});
  };

  const handleSave = () => {
    form.validateFields().then((values) => {
      api.post("/api/loyanui/instances", { type: selectedType, ...values }).then(() => {
        message.success(t("dashboard.created"));
        navigate("/adapters");
      }).catch(() => {});
    }).catch(() => {});
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.create_adapter")}</h2>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8 }}>{t("dashboard.select_type")}</div>
          <Select
            style={{ width: "100%" }}
            placeholder={t("dashboard.select_type_placeholder")}
            options={types.map((t) => ({ label: t, value: t }))}
            onChange={handleTypeChange}
          />
        </div>
        {schema && <DynamicForm schema={schema} form={form} />}
        <Button type="primary" onClick={handleSave} style={{ marginTop: 16 }}>
          {t("dashboard.save")}
        </Button>
      </Card>
    </div>
  );
}
