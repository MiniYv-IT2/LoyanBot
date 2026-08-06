import { useTranslation } from "react-i18next";
import { Input, Select, Switch, InputNumber } from "antd";

function parseOptions(desc) {
  const m = desc.match(/（([^）]+)）/)?.[1] || desc.match(/\(([^)]+)\)/)?.[1];
  return m && m.includes(" / ") ? m.split(" / ") : null;
}

export default function SchemaForm({ schema, values = {}, onChange, locale }) {
  const { i18n } = useTranslation();
  const lang = locale || i18n.language;
  const metadata = schema?.metadata || {};
  const i18nData = schema?.i18n || {};

  return Object.entries(metadata).map(([key, conf]) => {
    if (conf.showWhen && values[conf.showWhen.field] !== conf.showWhen.value) return null;
    const tKey = conf.description || key;
    const label = i18nData?.[lang]?.[tKey] || i18nData?.["zh-CN"]?.[tKey] || key;
    const hint = i18nData?.[lang]?.[conf.hint] || "";
    const desc = i18nData?.["zh-CN"]?.[tKey] || conf.description || "";
    const options = parseOptions(desc);
    const value = values[key];
    const setValue = (v) => onChange(key, v);

    const labelRow = (
      <div style={{ marginBottom: 4, fontSize: 13, color: "var(--text)" }}>
        {label}
        {conf.required && <span style={{ color: "#ff4d4f", marginLeft: 4 }}>*</span>}
      </div>
    );
    const hintRow = hint && (
      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{hint}</div>
    );

    if (conf.type === "bool") {
      return (
        <div key={key} style={{ marginBottom: 12 }}>
          {labelRow}
          <Switch checked={!!value} onChange={setValue} />
        </div>
      );
    }

    if (conf.type === "int") {
      return (
        <div key={key} style={{ marginBottom: 12 }}>
          {labelRow}
          <InputNumber style={{ width: "100%" }} value={value === undefined ? conf.default : value} onChange={setValue} />
          {hintRow}
        </div>
      );
    }

    if (conf.type === "list") {
      return (
        <div key={key} style={{ marginBottom: 12 }}>
          {labelRow}
          <Input
            value={(value ?? []).join(",")}
            onChange={(e) => setValue(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
          />
          {hintRow}
        </div>
      );
    }

    return (
      <div key={key} style={{ marginBottom: 12 }}>
        {labelRow}
        {options ? (
          <Select style={{ width: "100%" }} value={value === undefined ? conf.default : value} onChange={setValue}>
            {options.map((o) => (
              <Select.Option key={o} value={o}>{o}</Select.Option>
            ))}
          </Select>
        ) : conf.secret ? (
          <Input.Password value={value ?? ""} onChange={(e) => setValue(e.target.value)} />
        ) : (
          <Input value={value ?? ""} onChange={(e) => setValue(e.target.value)} />
        )}
        {hintRow}
      </div>
    );
  });
}
