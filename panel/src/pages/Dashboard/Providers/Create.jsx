import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Card, Button, Modal, List, Form, Input, message } from "antd";
import api from "../../../api";

const PRESETS = [
  { label: "ChatGPT", value: "chatgpt" },
  { label: "DeepSeek", value: "deepseek" },
  { label: "Groq", value: "groq" },
  { label: "Claude", value: "claude" },
  { label: "Gemini", value: "gemini" },
];

export default function ProviderCreate() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(true);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [form] = Form.useForm();

  const handleSelectPreset = (preset) => {
    setSelectedPreset(preset);
    setModalOpen(false);
  };

  const handleSave = () => {
    form.validateFields().then((values) => {
      api.post("/api/loyanui/providers", {
        provider: selectedPreset,
        id: values.id,
        api_key: values.api_key,
      }).then(() => {
        message.success(t("dashboard.created"));
        navigate("/providers");
      }).catch(() => {});
    }).catch(() => {});
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.create_provider")}</h2>
      <Modal
        title={t("dashboard.select_preset")}
        open={modalOpen}
        onCancel={() => navigate("/providers")}
        footer={null}
      >
        <List
          dataSource={PRESETS}
          renderItem={(item) => (
            <List.Item
              onClick={() => handleSelectPreset(item.value)}
              style={{ cursor: "pointer" }}
            >
              {item.label}
            </List.Item>
          )}
        />
      </Modal>
      {selectedPreset && (
        <Card>
          <Form form={form} layout="vertical">
            <Form.Item
              label={t("dashboard.id")}
              name="id"
              rules={[{ required: true, message: t("dashboard.required") }]}
            >
              <Input placeholder={t("dashboard.id_placeholder")} />
            </Form.Item>
            <Form.Item
              label={t("dashboard.api_key")}
              name="api_key"
              rules={[{ required: true, message: t("dashboard.required") }]}
            >
              <Input.Password placeholder={t("dashboard.api_key_placeholder")} />
            </Form.Item>
          </Form>
          <Button type="primary" onClick={handleSave}>
            {t("dashboard.save")}
          </Button>
        </Card>
      )}
    </div>
  );
}
