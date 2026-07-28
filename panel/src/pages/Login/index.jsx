import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Form, Input, Button, Card, Alert, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { login } from "../../api";
import logoSvg from "../../assets/images/Loyan.svg";
import Captcha from "../../components/Captcha";
import LanguageSelector from "../../components/LanguageSelector";

const ERROR_MAP = {
  "captcha.invalid": "login.captcha_invalid",
  "login.wrong": "login.wrong",
};

const BG = "#8ecac8";

export default function Login() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [captchaId, setCaptchaId] = useState("");
  const [captchaCode, setCaptchaCode] = useState("");
  const [captchaErr, setCaptchaErr] = useState(false);
  const navigate = useNavigate();

  const onFinishFailed = (errorInfo) => {
    console.error("Form validation failed:", errorInfo);
    setError(t("login.failed"));
  };

  const onFinish = async (values) => {
    if (!captchaCode) {
      setCaptchaErr(true);
      setError(t("captcha.required"));
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await login({
        username: values.username,
        password: values.password,
        captcha_id: captchaId,
        captcha_code: captchaCode,
      });
      if (res.data.success) {
        localStorage.setItem("token", res.data.token);
        message.success(t("login.success"));
        navigate("/");
      } else {
        setError(t("login.wrong"));
      }
    } catch (err) {
      const data = err.response?.data;
      const errCode = data?.error;
      const key = ERROR_MAP[errCode] || "login.failed";
      setError(t(key) + (data?.debug ? ` (${data.debug})` : ""));
      console.error("Login error:", errCode, data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "#FFC2D1",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0, left: 0, right: 0,
          height: 8,
          background: "#FF8FAB",
          borderBottom: "3px solid #000",
        }}
      />
      <div style={{ position: "absolute", top: 20, right: 20, zIndex: 10 }}>
        <LanguageSelector />
      </div>
      <Card
        style={{
          width: 380,
          textAlign: "center",
          background: "#fff",
        }}
      >
        <img
          src={logoSvg}
          alt="LoyanUI"
          style={{ width: 100, height: 100, marginBottom: 16 }}
        />
        <h2 style={{ margin: "0 0 4px", color: "#000", fontWeight: 900, fontSize: 24 }}>
          {t("app.title")}
        </h2>
        <p style={{ margin: "0 0 24px", color: "#000", fontWeight: 600 }}>
          {t("app.subtitle")}
        </p>
        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            closable
            onClose={() => setError("")}
            style={{ marginBottom: 16, border: "2px solid #000", borderRadius: 0 }}
          />
        )}
        <Form
          onFinish={onFinish}
          onFinishFailed={onFinishFailed}
          size="large"
          layout="vertical"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: t("login.required_user") }]}
          >
            <Input prefix={<UserOutlined />} placeholder={t("login.username")} />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: t("login.required_pwd") }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder={t("login.password")} />
          </Form.Item>
          <Form.Item label={t("captcha.placeholder")}>
            <div style={{ display: "flex", gap: 8 }}>
              <Input
                placeholder={t("captcha.placeholder")}
                onChange={(e) => {
                  setCaptchaCode(e.target.value);
                  setCaptchaErr(false);
                }}
                status={captchaErr ? "error" : undefined}
                style={{ flex: 1 }}
              />
              <Captcha
                onVerify={(id) => setCaptchaId(id)}
                style={{ flexShrink: 0 }}
              />
            </div>
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              block
              loading={loading}
            >
              {t("login.submit")}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
