import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { message, Modal, Spin, Switch } from "antd";

export default function PluginManage() {
  const { t } = useTranslation();
  const [plugins, setPlugins] = useState(null);
  const [busy, setBusy] = useState("");

  const load = async () => {
    try {
      const res = await fetch("/api/loyanui/plugins").then((r) => r.json());
      if (res.success) setPlugins(res.data || []);
      else setPlugins([]);
    } catch {
      setPlugins([]);
    }
  };

  useEffect(() => { load(); }, []);

  const doAction = async (p, action, okKey, failKey) => {
    if (busy) return;
    setBusy(p.name);
    try {
      const res = await fetch(`/api/loyanui/plugins/${p.name}/${action}`, { method: "POST" }).then((r) => r.json());
      if (res.success) {
        message.success(t(okKey));
      } else {
        message.error(res.message || t(failKey));
      }
    } catch {
      message.error(t(failKey));
    }
    setBusy("");
    load();
  };

  const doToggle = (p) => doAction(p, p.enabled ? "disable" : "enable", p.enabled ? "plugins.disableSuccess" : "plugins.enableSuccess", p.enabled ? "plugins.disableFailed" : "plugins.enableFailed");

  const doReinstall = (p) => doAction(p, "reinstall", "plugins.reinstallSuccess", "plugins.reinstallFailed");

  const doUninstall = (p) => {
    Modal.confirm({
      title: t("plugins.uninstallConfirmTitle"),
      content: t("plugins.uninstallConfirm", { name: p.display_name || p.name }),
      okText: t("common.confirm"),
      cancelText: t("common.cancel"),
      okType: "danger",
      centered: true,
      onOk: () => doAction(p, "remove", "plugins.uninstallSuccess", "plugins.uninstallFailed"),
    });
  };

  return (
    <div>
      <h2 style={{ margin: "0 0 24px", color: "var(--text)", fontSize: 22 }}>
        {t("plugins.manageTitle")}
      </h2>

      <div className="plugin-grid">
        {!plugins && (
          <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "center", padding: 60 }}>
            <Spin size="large" />
          </div>
        )}
        {plugins && plugins.length === 0 && (
          <div style={{ gridColumn: "1 / -1", textAlign: "center", color: "var(--text-secondary)", padding: 40 }}>
            {t("plugins.noPlugins")}
          </div>
        )}
        {plugins && plugins.map((p) => (
          <div key={p.name} className="plugin-card" style={{ background: "var(--card-bg)", border: "1px solid var(--sidebar-border)" }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              {p.icon ? (
                <img src={p.icon} alt="" referrerPolicy="no-referrer" style={{ width: 48, height: 48, borderRadius: 10, objectFit: "cover", flexShrink: 0 }} />
              ) : (
                <div style={{
                  width: 48, height: 48, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
                  background: "var(--primary)", color: "#fff", fontSize: 24, flexShrink: 0,
                }}>
                  {(p.display_name || p.name || "P").slice(0, 1)}
                </div>
              )}
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ color: "var(--text)", fontWeight: 600, fontSize: 15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.display_name || p.name}>
                  {p.display_name || p.name}
                </div>
                <div style={{ color: "var(--text-secondary)", fontSize: 12, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", lineHeight: "1.5", minHeight: 36, marginTop: 2 }} title={p.description}>
                  {p.description}
                </div>
              </div>
            </div>
            <div className="plugin-actions">
              <div className="pa-left">
                <span style={{ color: "var(--primary)", fontWeight: 600, fontSize: 12, alignSelf: "center" }}>v{p.version}</span>
              </div>
              <div className="pa-right">
                <button
                  onClick={() => doReinstall(p)}
                  disabled={busy === p.name}
                  style={{
                    padding: "3px 12px", borderRadius: 999, cursor: busy === p.name ? "default" : "pointer", fontSize: 12,
                    border: "1px solid var(--primary)", background: "var(--primary)", color: "#fff",
                    opacity: busy === p.name ? 0.5 : 1,
                  }}
                >
                  {t("plugins.reinstall")}
                </button>
                <button
                  onClick={() => doUninstall(p)}
                  disabled={busy === p.name}
                  style={{
                    padding: "3px 12px", borderRadius: 999, cursor: busy === p.name ? "default" : "pointer", fontSize: 12,
                    border: "1px solid #ff4d4f", background: "transparent", color: "#ff4d4f",
                    opacity: busy === p.name ? 0.5 : 1,
                  }}
                >
                  {t("plugins.uninstall")}
                </button>
                <Switch
                  checked={p.enabled}
                  loading={busy === p.name}
                  disabled={busy === p.name}
                  onChange={() => doToggle(p)}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
