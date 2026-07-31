import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { RobotOutlined, PlusOutlined, EditOutlined, DeleteOutlined, CheckOutlined, CloseOutlined, ReloadOutlined, QrcodeOutlined, FormOutlined, LoadingOutlined } from "@ant-design/icons";
import { Button, Drawer, List, Tag, Modal, Input, Select, Switch, InputNumber, Alert } from "antd";
import { useNavigate } from "react-router-dom";

import qqLogo from "../../../assets/platforms/qq.png";
import telegramLogo from "../../../assets/platforms/telegram.svg";
import onebotLogo from "../../../assets/platforms/onebot.png";
import satoriLogo from "../../../assets/platforms/satori.png";

const PLATFORM_META = {
  qq_official: { label: "QQ Official", logo: qqLogo },
  telegram: { label: "Telegram", logo: telegramLogo },
  onebot: { label: "OneBot v11 (QQ三方协议)", logo: onebotLogo },
  satori: { label: "Satori", logo: satoriLogo },
};

const ADAPTER_ORDER = ["onebot", "qq_official", "telegram", "satori"];

function fieldFromSchema(fieldKey, fieldConf, i18n, locale, value, onChange, formValues) {
  if (fieldConf.showWhen && formValues?.[fieldConf.showWhen.field] !== fieldConf.showWhen.value) return null;
  const tKey = fieldConf.description || fieldKey;
  const label = i18n?.[locale]?.[tKey] || i18n?.["zh-CN"]?.[tKey] || fieldKey;
  const hint = i18n?.[locale]?.[fieldConf.hint] || "";

  const desc = i18n?.["zh-CN"]?.[tKey] || fieldConf.description || "";
  const m = desc.match(/（([^）]+)）/)?.[1] || desc.match(/\(([^)]+)\)/)?.[1];
  const options = m && m.includes(" / ") ? m.split(" / ") : null;

  if (fieldConf.type === "bool") {
    return (
      <div key={fieldKey} style={{ marginBottom: 12 }}>
        <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{label}</div>
        <Switch checked={!!value} onChange={(v) => onChange(v)} />
      </div>
    );
  }

  if (fieldConf.type === "int") {
    return (
      <div key={fieldKey} style={{ marginBottom: 12 }}>
        <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{label}</div>
        <InputNumber style={{ width: "100%" }} value={value ?? fieldConf.default} onChange={(v) => onChange(v)} />
        {hint && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{hint}</div>}
      </div>
    );
  }

  if (fieldConf.type === "list") {
    return (
      <div key={fieldKey} style={{ marginBottom: 12 }}>
        <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{label}</div>
        <Input value={(value ?? []).join(",")} onChange={(e) => onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
        {hint && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{hint}</div>}
      </div>
    );
  }

  return (
    <div key={fieldKey} style={{ marginBottom: 12 }}>
      <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{label}
        {fieldConf.required && <span style={{ color: "#ff4d4f", marginLeft: 4 }}>*</span>}
      </div>
      {options ? (
        <Select style={{ width: "100%" }} value={value ?? fieldConf.default} onChange={(v) => onChange(v)}>
          {options.map((o) => <Select.Option key={o} value={o}>{o}</Select.Option>)}
        </Select>
      ) : fieldConf.secret ? (
        <Input.Password value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <Input value={value ?? ""} onChange={(e) => onChange(e.target.value)} />
      )}
      {hint && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{hint}</div>}
    </div>
  );
}

export default function AdaptersList() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [adapters, setAdapters] = useState(null);
  const [editItem, setEditItem] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedType, setSelectedType] = useState(null);
  const [schema, setSchema] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [editSchema, setEditSchema] = useState(null);
  const [editFormValues, setEditFormValues] = useState({});
  const [deleteItem, setDeleteItem] = useState(null);
  const [deleteAnswer, setDeleteAnswer] = useState("");
  const [mathProblem, setMathProblem] = useState({ a: 0, b: 0, op: "+" });
  const [notify, setNotify] = useState(null);
  const [loginMode, setLoginMode] = useState(null); // 'qr' | 'manual' | null
  const [qrTask, setQrTask] = useState(null);
  const [qrImg, setQrImg] = useState(null);
  const [qrExpired, setQrExpired] = useState(false);
  const [qrLoaded, setQrLoaded] = useState(false);

  const genMath = () => {
    const a = Math.floor(Math.random() * 50) + 1;
    const b = Math.floor(Math.random() * 50) + 1;
    const op = Math.random() > 0.5 ? "+" : "-";
    return { a, b, op };
  };

  const openDelete = (item) => {
    setDeleteItem(item);
    setDeleteAnswer("");
    setMathProblem(genMath());
  };

  const lang = i18n.language || "zh-CN";
  const locale = lang.startsWith("zh") ? "zh-CN" : lang.startsWith("ru") ? "ru-RU" : "en-US";

  const load = useCallback(() => {
    fetch("/api/loyanui/instances")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setAdapters(res.data);
      })
      .catch(() => setAdapters([]));
  }, []);

  useEffect(load, [load]);

  const openCreate = () => {
    setSelectedType(null);
    setSchema(null);
    setFormValues({});
    setCreateOpen(true);
    setNotify(null);
  };

  const selectType = async (type) => {
    setSelectedType(type);
    setNotify(null);
    setLoginMode(null);
    setQrTask(null);
    setQrImg(null);
    setQrExpired(false);
    if (type === "qq_official") {
      return; // wait for loginMode choice
    }
    await loadSchema(type);
  };

  const loadSchema = async (type) => {
    try {
      const res = await fetch(`/api/loyanui/adapter/schema/${type}`).then((r) => r.json());
      if (res.success) {
        const meta = res.data.metadata;
        setSchema(res.data);
        const defaults = {};
        for (const [k, v] of Object.entries(meta)) {
          if (v.default !== undefined) defaults[k] = v.default;
        }
        setFormValues(defaults);
      }
    } catch {
      setNotify({ type: "error", message: t("adapters.schema_failed") });
    }
  };

  const startQrLogin = async () => {
    setLoginMode("qr");
    setQrExpired(false);
    setQrLoaded(false);
    try {
      const primary = getComputedStyle(document.documentElement).getPropertyValue("--primary").trim().replace("#", "") || "8ecac8";
      const bg = getComputedStyle(document.documentElement).getPropertyValue("--card-bg").trim().replace("#", "") || "ffffff";
      const res = await fetch("/api/loyanui/qqbot/qr-login/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ color: primary, bgcolor: bg }),
      }).then((r) => r.json());
      if (res.success) {
        setQrTask({ task_id: res.data.task_id, bind_key: res.data.bind_key });
        setQrImg(res.data.qr_img);
        pollQrResult(res.data.task_id, res.data.bind_key);
      } else {
        setNotify({ type: "error", message: res.error || "QR create failed" });
      }
    } catch {
      setNotify({ type: "error", message: "QR create failed" });
    }
  };

  const pollQrResult = (taskId, bindKey) => {
    const poll = async () => {
      try {
        const res = await fetch("/api/loyanui/qqbot/qr-login/poll", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: taskId, bind_key: bindKey }),
        }).then((r) => r.json());
        if (res.success) {
          if (res.data.status === "scanned") {
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
            let suffix = "";
            for (let i = 0; i < 4; i++) suffix += chars[Math.floor(Math.random() * chars.length)];
            const botName = "QQClaw_" + suffix;
            const saveRes = await fetch("/api/loyanui/instances", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ name: botName, platform: "qq_official", bot_name: botName, app_id: res.data.appid, app_secret: res.data.secret, enabled: true }),
            }).then((r) => r.json());
            if (saveRes.success) {
              setNotify({ type: "success", message: `${t("adapters.qr_success")} ${botName}` });
              setTimeout(() => { setCreateOpen(false); load(); }, 1500);
            } else {
              setNotify({ type: "error", message: saveRes.error || t("adapters.save_failed") });
            }
            return;
          } else if (res.data.status === "expired") {
            setQrExpired(true);
            return;
          }
        }
        setTimeout(() => pollQrResult(taskId, bindKey), 2000);
      } catch {
        setTimeout(() => pollQrResult(taskId, bindKey), 2000);
      }
    };
    poll();
  };

  const validateRequired = (meta, values) => {
    for (const [k, conf] of Object.entries(meta)) {
      if (conf.required) {
        const v = values[k];
        if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) {
          const tKey = conf.description || k;
          const label = schema?.i18n?.[locale]?.[tKey] || schema?.i18n?.["zh-CN"]?.[tKey] || k;
          setNotify({ type: "warning", message: `${label} ${t("adapters.required_hint")}` });
          return false;
        }
      }
    }
    return true;
  };

  const loadEditForm = async (item) => {
    setNotify(null);
    try {
      const res = await fetch(`/api/loyanui/adapter/schema/${item.platform}`).then((r) => r.json());
      if (res.success) {
        setEditSchema(res.data);
        const vals = { enabled: item.enabled !== false };
        for (const [k, conf] of Object.entries(res.data.metadata)) {
          vals[k] = item[k] ?? conf.default;
        }
        setEditFormValues(vals);
      }
    } catch { /* ignore */ }
  };

  const handleSave = async () => {
    if (!validateRequired(schema?.metadata, formValues)) return;
    setSaving(true);
    try {
      const res = await fetch("/api/loyanui/instances", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: formValues.bot_name || selectedType, platform: selectedType, ...formValues }),
      }).then((r) => r.json());
      if (res.success) {
        setNotify({ type: "success", message: t("adapters.saved") });
        setTimeout(() => { setCreateOpen(false); load(); }, 800);
      } else {
        setNotify({ type: "error", message: res.error || t("adapters.save_failed") });
      }
    } catch {
      setNotify({ type: "error", message: t("adapters.save_failed") });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteItem) return;
    const numAnswer = parseInt(deleteAnswer, 10);
    if (isNaN(numAnswer)) { setNotify({ type: "warning", message: t("adapters.delete_wrong") }); return; }
    setSaving(true);
    try {
      const res = await fetch(`/api/loyanui/instances/${deleteItem._name}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ a: mathProblem.a, b: mathProblem.b, op: mathProblem.op, answer: numAnswer }),
      }).then((r) => r.json());
      if (res.success) {
        setNotify({ type: "success", message: t("adapters.delete_success") });
        setTimeout(() => { setDeleteItem(null); load(); }, 800);
      } else {
        setNotify({ type: "warning", message: res.error || t("adapters.delete_wrong") });
      }
    } catch {
      setNotify({ type: "error", message: t("adapters.save_failed") });
    } finally {
      setSaving(false);
    }
  };

  const handleEditSave = async () => {
    if (!editItem || !validateRequired(editSchema?.metadata, editFormValues)) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/loyanui/instances/${editItem._name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editFormValues),
      }).then((r) => r.json());
      if (res.success) {
        setNotify({ type: "success", message: t("adapters.saved") });
        setTimeout(() => { setEditItem(null); load(); }, 800);
      } else {
        setNotify({ type: "error", message: res.error || t("adapters.save_failed") });
      }
    } catch {
      setNotify({ type: "error", message: t("adapters.save_failed") });
    } finally {
      setSaving(false);
    }
  };

  if (adapters === null) return null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {t("app.add")}
        </Button>
      </div>

      {adapters.length === 0 ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh" }}>
          <RobotOutlined style={{ fontSize: 80, color: "#d9d9d9" }} />
          <p style={{ marginTop: 16, color: "var(--text-secondary)", fontSize: 14 }}>{t("adapters.empty")}</p>
        </div>
      ) : (
        <List
          dataSource={adapters}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button type="link" icon={<DeleteOutlined />} style={{ color: "var(--text-secondary)" }} onClick={() => openDelete(item)} />,
                <Button type="link" icon={<EditOutlined />} onClick={async () => { setEditItem(item); await loadEditForm(item); }} />,
              ]}
            >
              <List.Item.Meta
                title={
                  <span className="adapter-title">
                    <span className="adapter-name-line">
                      <span style={{ position: "relative", display: "inline-block", width: 20, height: 20, marginRight: 6, verticalAlign: "middle" }}>
                        <img src={PLATFORM_META[item.platform]?.logo} alt="" style={{ width: 20, height: 20 }} />
                        {item._status === "online" && <span style={{ position: "absolute", bottom: -1, right: -1, width: 8, height: 8, borderRadius: "50%", background: "#52c41a", border: "1.5px solid #fff" }} />}
                      </span>
                      {item.bot_name || item._name}
                    </span>
                    <span className="adapter-tags-line">
                      <Tag style={{ marginLeft: 8 }}>{PLATFORM_META[item.platform]?.label || item.platform}</Tag>
                      <Tag color={item.enabled ? "green" : "default"}>{item.enabled ? t("adapters.enabled") : t("adapters.disabled")}</Tag>
                    </span>
                  </span>
                }
              />
            </List.Item>
          )}
        />
      )}

      {/* 创建适配器弹窗 */}
      <Modal
        title={t("adapters.create_title")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        width={500}
        centered
        footer={
          selectedType && loginMode !== "qr" ? [
            <Button key="cancel" icon={<CloseOutlined />} onClick={() => setCreateOpen(false)}>{t("adapters.cancel")}</Button>,
            <Button key="save" type="primary" icon={<CheckOutlined />} loading={saving} onClick={handleSave}>{t("adapters.save")}</Button>,
          ] : null
        }
      >
        {notify && <Alert type={notify.type} message={notify.message} showIcon closable onClose={() => setNotify(null)} style={{ marginBottom: 12 }} />}
        {!selectedType ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {ADAPTER_ORDER.map((type) => {
              const meta = PLATFORM_META[type];
              return (
                <div
                  key={type}
                  onClick={() => selectType(type)}
                  style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "16px 12px", border: "1px solid #f0f0f0", borderRadius: 8,
                    cursor: "pointer", background: "#fafafa",
                  }}
                >
                  <img src={meta.logo} alt={meta.label} style={{ width: 36, height: 36, objectFit: "contain" }} />
                  <span style={{ fontSize: 14, color: "var(--text)" }}>{meta.label}</span>
                </div>
              );
            })}
          </div>
        ) : loginMode === "qr" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: "20px 0", position: "relative" }}>
            {!qrLoaded && <div style={{ width: 250, height: 250, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-secondary)" }}><LoadingOutlined style={{ fontSize: 32 }} /></div>}
            <img src={qrImg} alt="QR Code" onLoad={() => setQrLoaded(true)} style={{ width: 250, height: 250, display: qrLoaded ? "block" : "none" }} />
            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{t("adapters.qr_hint")}</span>
            {qrExpired && (
              <div onClick={startQrLogin} style={{ position: "absolute", inset: 0, background: "rgba(255,255,255,0.85)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", borderRadius: 8 }}>
                <div style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 32, color: "var(--primary)" }}><ReloadOutlined /></div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{t("adapters.qr_expired")}</div>
                </div>
              </div>
            )}
          </div>
        ) : selectedType === "qq_official" && !loginMode ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, padding: 8, background: "#f5f5f5", borderRadius: 6 }}>
              <img src={PLATFORM_META["qq_official"]?.logo} alt="" style={{ width: 24, height: 24 }} />
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{PLATFORM_META["qq_official"]?.label}</span>
            </div>
            <div onClick={() => { setLoginMode("qr"); startQrLogin(); }} style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 12px", border: "1px solid var(--sidebar-border)", borderRadius: 8, cursor: "pointer", background: "var(--card-bg)" }}>
              <span style={{ fontSize: 24 }}><QrcodeOutlined /></span>
              <span style={{ fontSize: 14, color: "var(--text)" }}>{t("adapters.qr_title")}</span>
            </div>
            <div onClick={() => { setLoginMode("manual"); loadSchema("qq_official"); }} style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 12px", border: "1px solid var(--sidebar-border)", borderRadius: 8, cursor: "pointer", background: "var(--card-bg)" }}>
              <span style={{ fontSize: 24 }}><FormOutlined /></span>
              <span style={{ fontSize: 14, color: "var(--text)" }}>{t("adapters.manual_title")}</span>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: 8, background: "#f5f5f5", borderRadius: 6, cursor: "pointer" }} onClick={() => selectType(selectedType)}>
              <img src={PLATFORM_META[selectedType]?.logo} alt="" style={{ width: 24, height: 24 }} />
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{PLATFORM_META[selectedType]?.label}</span>
            </div>
            <div key="enabled" style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 13, color: "var(--text)" }}>{formValues.enabled !== false ? t("adapters.enabled") : t("adapters.disabled")}</span>
              <Switch checked={formValues.enabled !== false} onChange={(v) => setFormValues((prev) => ({ ...prev, enabled: v }))} />
            </div>
            {schema && Object.entries(schema.metadata).map(([k, conf]) =>
              fieldFromSchema(k, conf, schema.i18n, locale, formValues[k], (v) => setFormValues((prev) => ({ ...prev, [k]: v })), formValues)
            )}
          </div>
        )}
      </Modal>

      <Modal
        title={t("adapters.delete_title")}
        open={!!deleteItem}
        onCancel={() => setDeleteItem(null)}
        centered
        width={400}
        footer={[
          <Button key="cancel" onClick={() => setDeleteItem(null)}>{t("adapters.cancel")}</Button>,
          <Button key="delete" danger type="primary" loading={saving} onClick={handleDelete}>{t("adapters.delete")}</Button>,
        ]}
      >
        {notify && <Alert type={notify.type} message={notify.message} showIcon closable onClose={() => setNotify(null)} style={{ marginBottom: 12 }} />}
        <p>{t("adapters.delete_confirm")}</p>
        <div style={{ fontSize: 24, textAlign: "center", margin: "16px 0", fontWeight: 700 }}>
          {mathProblem.a} {mathProblem.op} {mathProblem.b} = ?
        </div>
        <form onSubmit={(e) => { e.preventDefault(); handleDelete(); }}>
          <Input
            value={deleteAnswer}
            onChange={(e) => setDeleteAnswer(e.target.value)}
            placeholder="?"
            autoComplete="off"
            name=""
            style={{ textAlign: "center", fontSize: 18 }}
          />
        </form>
      </Modal>

      <Drawer
        title={`${t("adapters.edit_title")} ${editItem?.bot_name || editItem?._name || ""}`}
        placement="right"
        width={400}
        open={!!editItem}
        onClose={() => setEditItem(null)}
        footer={
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button icon={<CloseOutlined />} onClick={() => setEditItem(null)}>{t("adapters.cancel")}</Button>
            <Button type="primary" icon={<CheckOutlined />} loading={saving} onClick={handleEditSave}>{t("adapters.save")}</Button>
          </div>
        }
      >
        {notify && <Alert type={notify.type} message={notify.message} showIcon closable onClose={() => setNotify(null)} style={{ marginBottom: 12 }} />}
        <div key="edit-enabled" style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: "var(--text)" }}>{editFormValues.enabled !== false ? t("adapters.enabled") : t("adapters.disabled")}</span>
          <Switch checked={editFormValues.enabled !== false} onChange={(v) => setEditFormValues((prev) => ({ ...prev, enabled: v }))} />
        </div>
        {editSchema && Object.entries(editSchema.metadata).map(([k, conf]) => {
          const v = editFormValues[k];
          return fieldFromSchema(k, conf, editSchema.i18n, locale, v, (nv) => setEditFormValues((prev) => ({ ...prev, [k]: nv })), editFormValues);
        })}
      </Drawer>
    </div>
  );
}
