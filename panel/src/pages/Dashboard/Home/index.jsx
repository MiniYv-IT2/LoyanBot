import { useTranslation } from "react-i18next";

const BG = "#8ecac8";

export default function DashboardHome() {
  const { t } = useTranslation();

  return (
    <div>
      <h2 style={{ margin: "0 0 24px", color: "#333", fontSize: 22 }}>
        {t("dashboard.welcome")}
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 16,
        }}
      >
        {["消息量", "命令数", "运行时间", "插件数"].map((label) => (
          <div
            key={label}
            style={{
              background: "#fafafa",
              border: "1px solid #f0f0f0",
              borderRadius: 8,
              padding: "20px 16px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700, color: BG }}>
              --
            </div>
            <div style={{ fontSize: 13, color: "#999", marginTop: 4 }}>
              {label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
