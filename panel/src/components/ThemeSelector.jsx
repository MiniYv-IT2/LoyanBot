import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { SkinOutlined } from "@ant-design/icons";
import { Dropdown, Space } from "antd";

const THEMES = [
  { key: "mist", color: "#8ecac8" },
  { key: "white", color: "#ffffff" },
  { key: "pink", color: "#f0a8c8" },
  { key: "purple", color: "#b8a0d0" },
  { key: "orange", color: "#f0a060" },
  { key: "dark", color: "#1a1a2e" },
];

export default function ThemeSelector() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState(() => localStorage.getItem("loyan-theme") || "mist");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("loyan-theme", theme);
  }, [theme]);

  const items = THEMES.map((th) => ({
    key: th.key,
    label: (
      <Space>
        <span style={{ display: "inline-block", width: 12, height: 12, borderRadius: "50%", background: th.color, border: "1px solid #d9d9d9" }} />
        {t(`theme.${th.key}`)}
      </Space>
    ),
    onClick: () => setTheme(th.key),
  }));

  return (
    <Dropdown menu={{ items }} trigger={["click"]} placement="bottomRight">
      <span style={{ cursor: "pointer", fontSize: 16, color: "var(--sidebar-icon)", padding: "0 8px" }}>
        <SkinOutlined />
      </span>
    </Dropdown>
  );
}
