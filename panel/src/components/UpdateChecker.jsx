import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Modal, message } from "antd";
import { CloudDownloadOutlined, LoadingOutlined } from "@ant-design/icons";

export default function UpdateChecker() {
  const { t } = useTranslation();
  const [info, setInfo] = useState(null);
  const [open, setOpen] = useState(false);
  const [applying, setApplying] = useState(false);

  const check = () => {
    fetch("/api/loyanui/update/check")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setInfo(res.data);
      })
      .catch(() => {});
  };

  useEffect(() => {
    check();
    const timer = setInterval(check, 30 * 60 * 1000);
    return () => clearInterval(timer);
  }, []);

  const apply = async () => {
    setApplying(true);
    try {
      const res = await fetch("/api/loyanui/update/apply", { method: "POST" }).then((r) => r.json());
      const data = res.data || {};
      if (data.success) {
        message.success(t("updates.updateSuccess"));
        setOpen(false);
      } else if (data.pip) {
        message.info(data.message || t("updates.updateFailed"));
        setOpen(false);
      } else {
        message.error(data.message || t("updates.updateFailed"));
      }
    } catch {
      message.error(t("updates.updateFailed"));
    } finally {
      setApplying(false);
    }
  };

  const available = !!(info && info.available);
  const changelog = (info && info.changelog) || "";

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {available && (
          <span style={{ color: "var(--primary)", fontSize: 13, whiteSpace: "nowrap" }}>
            {t("updates.newVersionFound")} v{info.latest}
          </span>
        )}
        <Button
          type="text"
          icon={available ? <CloudDownloadOutlined style={{ color: "var(--primary)" }} /> : <CloudDownloadOutlined />}
          onClick={() => setOpen(true)}
          title={t("updates.checkUpdate")}
        />
      </div>
      <Modal
        title={`${t("updates.newVersionFound")} ${info && info.latest ? `v${info.latest}` : ""}`}
        open={open}
        onCancel={() => setOpen(false)}
        footer={
          available ? [
            <Button key="later" onClick={() => setOpen(false)}>{t("updates.updateLater")}</Button>,
            <Button key="apply" type="primary" icon={applying ? <LoadingOutlined /> : <CloudDownloadOutlined />} loading={applying} onClick={apply}>
              {t("updates.updateNow")}
            </Button>,
          ] : [
            <Button key="close" onClick={() => setOpen(false)}>{t("common.close")}</Button>,
          ]
        }
      >
        {!available && <div style={{ color: "var(--text-secondary)", padding: "12px 0" }}>{t("updates.noUpdate")}</div>}
        {changelog && (
          <div
            style={{
              maxHeight: 320,
              overflowY: "auto",
              fontSize: 13,
              color: "var(--text)",
              lineHeight: 1.7,
              whiteSpace: "pre-wrap",
            }}
          >
            {changelog}
          </div>
        )}
      </Modal>
    </>
  );
}
