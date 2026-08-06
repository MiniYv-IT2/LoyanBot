import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiOutlined, PlusOutlined, EditOutlined, DeleteOutlined, CloseOutlined, CheckOutlined } from "@ant-design/icons";
import { Button, Drawer, Input, Modal, Segmented, Spin, Switch } from "antd";
import { message } from "antd";
import SchemaForm from "../../../components/SchemaForm";

// 厂商 logo：批量导入项目外资源目录（vite build 支持 import 项目外文件）
const ICON_PREFIX = "../../../../../loyan/res/resource/providers/";
const icons = import.meta.glob("../../../../../loyan/res/resource/providers/*", { eager: true, import: "default" });

const CATEGORY_OPTIONS = [
  { key: "chat", labelKey: "providers.categoryChat" },
  { key: "tts", labelKey: "providers.categoryTts" },
  { key: "embedding", labelKey: "providers.categoryEmbedding" },
];

// 落在实例 extra 里的字段（表列之外的配置）
const EXTRA_FIELDS = ["model_prefix", "timeout", "max_retries", "strip_think", "custom_models", "custom_pricing"];

function VendorAvatar({ icon, name, size = 40 }) {
  const src = icon && icons[ICON_PREFIX + icon];
  if (src) {
    return <img src={src} alt="" referrerPolicy="no-referrer" style={{ width: size, height: size, objectFit: "contain", flexShrink: 0 }} />;
  }
  return (
    <div style={{
      width: size, height: size, borderRadius: 8, flexShrink: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--primary)", color: "#fff", fontSize: Math.round(size * 0.5), fontWeight: 600,
    }}>
      {(name || "P").slice(0, 1)}
    </div>
  );
}

function matchVendor(inst, vendors) {
  const extra = inst?.extra || {};
  if (extra.vendor) {
    const v = vendors.find((x) => x.id === extra.vendor);
    if (v) return v;
  }
  if (extra.model_prefix) {
    const v = vendors.find((x) => x.prefix === extra.model_prefix);
    if (v) return v;
  }
  if (inst?.api_base) {
    const v = vendors.find((x) => x.api_base && x.api_base === inst.api_base);
    if (v) return v;
  }
  return null;
}

function pricingToText(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export default function ProvidersList() {
  const { t, i18n } = useTranslation();
  const locale = i18n.language.startsWith("zh") ? "zh-CN" : i18n.language.startsWith("ru") ? "ru-RU" : "en-US";

  const [providers, setProviders] = useState(null);
  const [vendors, setVendors] = useState([]);
  const [usage, setUsage] = useState(null);
  const [catFilter, setCatFilter] = useState("chat");

  // 创建
  const [createOpen, setCreateOpen] = useState(false);
  const [createStep, setCreateStep] = useState("pick"); // 'pick' | 'form'
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [schema, setSchema] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [testState, setTestState] = useState({ loading: false, ok: null, msg: "" });

  // 编辑
  const [editItem, setEditItem] = useState(null);
  const [editValues, setEditValues] = useState({});

  // 删除
  const [deleteItem, setDeleteItem] = useState(null);
  const [deleteAnswer, setDeleteAnswer] = useState("");
  const [mathProblem, setMathProblem] = useState({ a: 0, b: 0, op: "+" });

  const [winW, setWinW] = useState(typeof window !== "undefined" ? window.innerWidth : 1280);

  useEffect(() => {
    const onResize = () => setWinW(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const load = useCallback(() => {
    fetch("/api/loyanui/providers")
      .then((r) => r.json())
      .then((res) => setProviders(res.success ? res.data || [] : []))
      .catch(() => setProviders([]));
    fetch("/api/loyanui/providers/usage")
      .then((r) => r.json())
      .then((res) => { if (res.success) setUsage(res.data); })
      .catch(() => setUsage(null));
  }, []);

  useEffect(() => {
    load();
    fetch("/api/loyanui/providers/vendors")
      .then((r) => r.json())
      .then((res) => { if (res.success) setVendors(res.data || []); })
      .catch(() => setVendors([]));
    // 统一 litellm schema（创建/编辑共用，接口不通时降级为简单表单）
    fetch("/api/loyanui/adapter/schema/litellm")
      .then((r) => r.json())
      .then((res) => { if (res.success) setSchema(res.data); })
      .catch(() => setSchema(null));
  }, [load]);

  // SchemaForm 用 schema：剔除 custom_pricing（单独 JSON 文本框），注入 api_key 多 key 提示
  const formSchema = useMemo(() => {
    if (!schema) return null;
    const metadata = {};
    for (const [k, v] of Object.entries(schema.metadata || {})) {
      if (k === "custom_pricing") continue;
      metadata[k] = k === "api_key" ? { ...v, hint: "providers.apiKeyHint" } : { ...v };
    }
    const i18nData = {};
    for (const lang of ["zh-CN", "en-US", "ru-RU"]) {
      i18nData[lang] = {
        ...(schema.i18n?.[lang] || {}),
        "providers.apiKeyHint": i18n.t("providers.apiKeyHint", { lng: lang }),
      };
    }
    return { metadata, i18n: i18nData };
  }, [schema, i18n]);

  const schemaDefaults = useMemo(() => {
    const out = {};
    if (schema) {
      for (const [k, v] of Object.entries(schema.metadata || {})) {
        if (k === "custom_pricing") continue;
        if (v.default !== undefined) out[k] = v.default;
      }
    }
    return out;
  }, [schema]);

  const filteredVendors = catFilter ? vendors.filter((v) => (v.category || []).includes(catFilter)) : vendors;

  const visibleProviders = useMemo(() => {
    if (!providers) return null;
    if (!catFilter) return providers;
    return providers.filter((p) => {
      const v = matchVendor(p, vendors);
      return v && (v.category || []).includes(catFilter);
    });
  }, [providers, vendors, catFilter]);

  const genMath = () => {
    const a = Math.floor(Math.random() * 50) + 1;
    const b = Math.floor(Math.random() * 50) + 1;
    const op = Math.random() > 0.5 ? "+" : "-";
    return { a, b, op };
  };

  // ── 创建 ──

  const openCreate = () => {
    setCreateStep("pick");
    setSelectedVendor(null);
    setFormValues({});
    resetTest();
    setCreateOpen(true);
  };

  const selectVendor = (v) => {
    resetTest();
    setSelectedVendor(v);
    setFormValues({
      ...schemaDefaults,
      id: "",
      api_key: "",
      api_base: v.api_base || "",
      model_prefix: v.prefix || "",
      custom_pricing: "",
      enabled: true,
    });
    setCreateStep("form");
  };


  const testConnection = async (values, setter) => {
    setter({ loading: true, ok: null, msg: "" });
    try {
      const res = await fetch("/api/loyanui/providers/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_base: values.api_base || "", api_key: values.api_key || "" }),
      }).then((r) => r.json());
      setter({
        loading: false,
        ok: !!res.success,
        msg: res.success ? t("providers.testSuccess") : (res.message || t("providers.testFailed")),
      });
    } catch {
      setter({ loading: false, ok: false, msg: t("providers.testFailed") });
    }
  };

  const resetTest = () => setTestState({ loading: false, ok: null, msg: "" });

  const parsePricing = (text) => {
    if (!text || !text.trim()) return {};
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      return null;
    }
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return null;
    return parsed;
  };

  const handleCreate = async () => {
    if (!selectedVendor) return;
    const id = (formValues.id || "").trim();
    if (!id) {
      message.warning(`${t("providers.instanceId")} ${t("common.required")}`);
      return;
    }
    const pricing = parsePricing(formValues.custom_pricing);
    if (pricing === null) {
      message.warning(t("providers.customPricingInvalid"));
      return;
    }
    setSaving(true);
    const extra = { vendor: selectedVendor.id };
    for (const k of EXTRA_FIELDS) {
      if (k === "custom_pricing") extra[k] = pricing;
      else if (formValues[k] !== undefined) extra[k] = formValues[k];
    }
    try {
      const res = await fetch("/api/loyanui/providers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id,
          type: "litellm",
          model: "",
          api_base: formValues.api_base || "",
          api_key: formValues.api_key || "",
          enabled: formValues.enabled !== false,
          extra,
        }),
      }).then((r) => r.json());
      if (res.success) {
        message.success(t("providers.created"));
        resetTest();
        setCreateOpen(false);
        load();
      } else {
        const msg = res.message || "";
        message.error(/unique|already exists|重复|已存在/i.test(msg) ? t("providers.idExists") : msg || t("providers.saveFailed"));
      }
    } catch {
      message.error(t("providers.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  // ── 编辑 ──

  const openEdit = (item) => {
    resetTest();
    setEditItem(item);
    const extra = item.extra || {};
    setEditValues({
      api_key: item.api_key || "",
      api_base: item.api_base || "",
      model_prefix: extra.model_prefix ?? schemaDefaults.model_prefix ?? "",
      timeout: extra.timeout ?? schemaDefaults.timeout ?? 60,
      max_retries: extra.max_retries ?? schemaDefaults.max_retries ?? 3,
      strip_think: extra.strip_think ?? schemaDefaults.strip_think ?? true,
      custom_models: extra.custom_models ?? schemaDefaults.custom_models ?? [],
      custom_pricing: pricingToText(extra.custom_pricing),
      enabled: item.enabled !== false,
    });
  };

  const toggleEnabled = async (v) => {
    if (!editItem || saving) return;
    setEditValues((prev) => ({ ...prev, enabled: v }));
    setSaving(true);
    try {
      const res = await fetch(`/api/loyanui/providers/${encodeURIComponent(editItem.id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: v }),
      }).then((r) => r.json());
      if (res.success) {
        message.success(t("providers.saved"));
        load();
      } else {
        message.error(res.message || t("providers.saveFailed"));
        setEditValues((prev) => ({ ...prev, enabled: !v }));
      }
    } catch {
      message.error(t("providers.saveFailed"));
      setEditValues((prev) => ({ ...prev, enabled: !v }));
    } finally {
      setSaving(false);
    }
  };

  const handleEditSave = async () => {
    if (!editItem) return;
    const pricing = parsePricing(editValues.custom_pricing);
    if (pricing === null) {
      message.warning(t("providers.customPricingInvalid"));
      return;
    }
    setSaving(true);
    const extra = { ...(editItem.extra || {}) };
    for (const k of EXTRA_FIELDS) {
      if (k === "custom_pricing") extra[k] = pricing;
      else if (editValues[k] !== undefined) extra[k] = editValues[k];
    }
    try {
      const res = await fetch(`/api/loyanui/providers/${encodeURIComponent(editItem.id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: editValues.api_key || "",
          api_base: editValues.api_base || "",
          enabled: editValues.enabled !== false,
          extra,
        }),
      }).then((r) => r.json());
      if (res.success) {
        message.success(t("providers.saved"));
        resetTest();
        setEditItem(null);
        load();
      } else {
        message.error(res.message || t("providers.saveFailed"));
      }
    } catch {
      message.error(t("providers.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  // ── 删除 ──

  const openDelete = (item) => {
    setDeleteItem(item);
    setDeleteAnswer("");
    setMathProblem(genMath());
  };

  const handleDelete = async () => {
    if (!deleteItem) return;
    const ans = parseInt(deleteAnswer, 10);
    if (isNaN(ans)) {
      message.warning(t("providers.verificationWrong"));
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`/api/loyanui/providers/${encodeURIComponent(deleteItem.id)}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ a: mathProblem.a, b: mathProblem.b, op: mathProblem.op, answer: ans }),
      }).then((r) => r.json());
      if (res.success) {
        message.success(t("providers.deleted"));
        setDeleteItem(null);
        resetTest();
        setEditItem(null);
        load();
      } else if (res.error === "verification_wrong") {
        message.warning(t("providers.verificationWrong"));
      } else {
        message.error(res.message || t("providers.deleteFailed"));
      }
    } catch {
      message.error(t("providers.deleteFailed"));
    } finally {
      setSaving(false);
    }
  };

  const editVendor = editItem ? matchVendor(editItem, vendors) : null;

  return (
    <div>
      {/* 标题行：标题左 + 添加按钮右 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0, color: "var(--text)", fontSize: 22 }}>{t("sidebar.providers")}</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          {t("common.add")}
        </Button>
      </div>

      {/* 分类标签：居中，控制添加弹窗里的厂商过滤 */}
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
        <Segmented
          options={CATEGORY_OPTIONS.map((c) => ({ label: t(c.labelKey), value: c.key }))}
          value={catFilter}
          onChange={(v) => setCatFilter(v)}
        />
      </div>

      {usage && (
        <div style={{ display: "flex", justifyContent: "center", flexWrap: "wrap", gap: 8, marginBottom: 16, fontSize: 13, color: "var(--text-secondary)" }}>
          <span>{t("providers.usageTitle")}:</span>
          <span>{t("providers.calls")} {usage.total_calls ?? 0}</span>
          <span>{t("common.failed")} {usage.failed ?? 0}</span>
          <span>{t("providers.tokens")} {usage.total_tokens ?? 0}</span>
          <span>{t("providers.cost")} ¥{usage.total_cost ?? "0.00"}</span>
        </div>
      )}

      {providers === null ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : (visibleProviders || []).length === 0 ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "50vh" }}>
          <ApiOutlined style={{ fontSize: 80, color: "#d9d9d9" }} />
          <p style={{ marginTop: 16, color: "var(--text-secondary)", fontSize: 14 }}>{catFilter ? t("providers.noVendor") : t("providers.empty")}</p>
        </div>
      ) : (
        <div className="provider-grid">
          {(visibleProviders || []).map((p) => {
            const vendor = matchVendor(p, vendors);
            return (
              <div key={p.id} className="provider-card" style={{ background: "var(--card-bg)", border: "1px solid var(--sidebar-border)" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 10, minWidth: 0 }}>
                  <VendorAvatar icon={vendor?.icon} name={vendor?.name || p.type || p.id} size={40} />
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ color: "var(--text)", fontWeight: 700, fontSize: 15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.id}>
                      {p.id}
                    </div>
                    <div style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={vendor?.name || p.type}>
                      {vendor?.name || p.type}
                    </div>
                    <div style={{ color: "var(--text-secondary)", fontSize: 12, marginTop: 2, opacity: 0.85, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.api_base || vendor?.api_base || "-"}>
                      {p.api_base || vendor?.api_base || "-"}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <Button type="text" icon={<EditOutlined />} style={{ color: "var(--text-secondary)" }} title={t("common.edit")} onClick={() => openEdit(p)} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 添加弹窗：先选厂商，再配置实例 */}
      <Modal
        title={createStep === "pick" ? t("providers.selectVendor") : selectedVendor?.name || t("providers.configTitle")}
        open={createOpen}
        onCancel={() => { resetTest(); setCreateOpen(false); }}
        width={createStep === "pick" ? 480 : 520}
        centered
        footer={createStep === "pick" ? null : [
          <Button key="cancel" icon={<CloseOutlined />} onClick={() => { resetTest(); setCreateOpen(false); }}>{t("common.cancel")}</Button>,
          <Button key="test" icon={<ApiOutlined />} loading={testState.loading} onClick={() => testConnection(formValues, setTestState)}>{t("providers.testConnection")}</Button>,
          <Button key="save" type="primary" icon={<CheckOutlined />} loading={saving} onClick={handleCreate}>{t("common.save")}</Button>,
        ]}
      >
        {createStep === "pick" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 420, overflowY: "auto" }}>
            {filteredVendors.length === 0 && (
              <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: 24 }}>{t("providers.noVendor")}</div>
            )}
            {filteredVendors.map((v) => (
              <div
                key={v.id}
                onClick={() => selectVendor(v)}
                style={{
                  display: "flex", alignItems: "center", gap: 12, padding: "12px",
                  border: "1px solid var(--sidebar-border)", borderRadius: 8,
                  cursor: "pointer", background: "var(--card-bg)",
                }}
              >
                <VendorAvatar icon={v.icon} name={v.name} size={36} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 14, color: "var(--text)" }}>{v.name}</div>
                  {v.note && (
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v.note}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: 8, background: "var(--bg-mid)", borderRadius: 6 }}>
              <VendorAvatar icon={selectedVendor?.icon} name={selectedVendor?.name} size={24} />
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{selectedVendor?.name}</span>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>
                {t("providers.instanceId")} <span style={{ color: "#ff4d4f", marginLeft: 4 }}>*</span>
              </div>
              <Input
                value={formValues.id || ""}
                onChange={(e) => setFormValues((prev) => ({ ...prev, id: e.target.value }))}
                placeholder={t("providers.instanceIdPlaceholder")}
                autoComplete="off"
              />
            </div>
            <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: 13, color: "var(--text)" }}>{formValues.enabled !== false ? t("common.enable") : t("common.disable")}</span>
              <Switch checked={formValues.enabled !== false} onChange={(v) => setFormValues((prev) => ({ ...prev, enabled: v }))} />
            </div>
            {formSchema ? (
              <SchemaForm schema={formSchema} values={formValues} onChange={(k, v) => setFormValues((prev) => ({ ...prev, [k]: v }))} locale={locale} />
            ) : (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.apiKey")}</div>
                  <Input.Password value={formValues.api_key || ""} onChange={(e) => setFormValues((prev) => ({ ...prev, api_key: e.target.value }))} placeholder={t("providers.apiKeyPlaceholder")} />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.baseUrl")}</div>
                  <Input value={formValues.api_base || ""} onChange={(e) => setFormValues((prev) => ({ ...prev, api_base: e.target.value }))} />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.modelPrefix")}</div>
                  <Input value={formValues.model_prefix || ""} onChange={(e) => setFormValues((prev) => ({ ...prev, model_prefix: e.target.value }))} />
                </div>
              </div>
            )}
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.customPricing")}</div>
              <Input.TextArea
                rows={3}
                value={formValues.custom_pricing || ""}
                onChange={(e) => setFormValues((prev) => ({ ...prev, custom_pricing: e.target.value }))}
                placeholder={t("providers.customPricingHint")}
                autoComplete="off"
              />
            </div>
          </div>
        )}
        {testState.msg && (
          <div style={{ marginTop: 8, fontSize: 13, color: testState.ok ? "#52c41a" : "#ff4d4f" }}>{testState.msg}</div>
        )}
      </Modal>

      {/* 编辑抽屉 */}
      <Drawer
        title={`${t("common.edit")} ${editItem?.id || ""}`}
        placement="right"
        width={winW < 768 ? "100%" : 400}
        open={!!editItem}
        onClose={() => setEditItem(null)}
        footer={
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => openDelete(editItem)}>{t("common.delete")}</Button>
            <div style={{ display: "flex", gap: 6 }}>
              <Button size="small" icon={<CloseOutlined />} onClick={() => setEditItem(null)}>{t("common.cancel")}</Button>
              <Button size="small" icon={<ApiOutlined />} loading={testState.loading} onClick={() => testConnection(editValues, setTestState)}>{t("providers.testConnection")}</Button>
              <Button size="small" type="primary" icon={<CheckOutlined />} loading={saving} onClick={handleEditSave}>{t("common.save")}</Button>
            </div>
          </div>
        }
      >
        {editItem && (
          <div>
            <div style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ color: "var(--text)", fontWeight: 600 }}>{editItem.id}</div>
                <div style={{ color: "var(--text-secondary)", fontSize: 12 }}>{editVendor?.name || editItem.type}</div>
              </div>
              <Switch checked={editValues.enabled !== false} loading={saving} onChange={toggleEnabled} />
            </div>
            {formSchema ? (
              <SchemaForm schema={formSchema} values={editValues} onChange={(k, v) => setEditValues((prev) => ({ ...prev, [k]: v }))} locale={locale} />
            ) : (
              <div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.apiKey")}</div>
                  <Input.Password value={editValues.api_key || ""} onChange={(e) => setEditValues((prev) => ({ ...prev, api_key: e.target.value }))} placeholder={t("providers.apiKeyPlaceholder")} />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.baseUrl")}</div>
                  <Input value={editValues.api_base || ""} onChange={(e) => setEditValues((prev) => ({ ...prev, api_base: e.target.value }))} />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.modelPrefix")}</div>
                  <Input value={editValues.model_prefix || ""} onChange={(e) => setEditValues((prev) => ({ ...prev, model_prefix: e.target.value }))} />
                </div>
              </div>
            )}
            <div style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>{t("providers.customPricing")}</div>
              <Input.TextArea
                rows={3}
                value={editValues.custom_pricing || ""}
                onChange={(e) => setEditValues((prev) => ({ ...prev, custom_pricing: e.target.value }))}
                placeholder={t("providers.customPricingHint")}
                autoComplete="off"
              />
            </div>
          </div>
        )}
        {testState.msg && (
          <div style={{ marginTop: 8, fontSize: 13, color: testState.ok ? "#52c41a" : "#ff4d4f" }}>{testState.msg}</div>
        )}
      </Drawer>

      {/* 删除确认（数学题验证） */}
      <Modal
        title={t("providers.deleteTitle")}
        open={!!deleteItem}
        onCancel={() => setDeleteItem(null)}
        centered
        width={400}
        footer={[
          <Button key="cancel" onClick={() => setDeleteItem(null)}>{t("common.cancel")}</Button>,
          <Button key="delete" danger type="primary" loading={saving} onClick={handleDelete}>{t("common.delete")}</Button>,
        ]}
      >
        <p>{t("providers.deleteConfirm")}</p>
        <div style={{ fontSize: 24, textAlign: "center", margin: "16px 0", fontWeight: 700 }}>
          {mathProblem.a} {mathProblem.op} {mathProblem.b} = ?
        </div>
        <form onSubmit={(e) => { e.preventDefault(); handleDelete(); }}>
          <Input
            value={deleteAnswer}
            onChange={(e) => setDeleteAnswer(e.target.value)}
            placeholder={t("providers.mathProblem")}
            autoComplete="off"
            name=""
            style={{ textAlign: "center", fontSize: 18 }}
          />
        </form>
      </Modal>
    </div>
  );
}
