import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import api from "../../../api";

const BG = "#8ecac8";

export default function DashboardHome() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/api/loyanui/stats").then((res) => setStats(res.data)).catch(() => {});
  }, []);

  const cards = [
    { key: "messages", label: t("dashboard.stats.messages"), value: stats?.messages },
    { key: "commands", label: t("dashboard.stats.commands"), value: stats?.commands },
    { key: "uptime", label: t("dashboard.stats.uptime"), value: stats?.uptime },
    { key: "plugins", label: t("dashboard.stats.plugins"), value: stats?.plugins },
  ];

  const adaptersOnline = stats?.adapters_online ?? "--";
  const adaptersTotal = stats?.adapters_total ?? "--";

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
        {cards.map((card) => (
          <div
            key={card.key}
            className="nb-stat-card"
            style={{
              padding: "20px 16px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700, color: "#000" }}>
              {card.value ?? "--"}
            </div>
            <div style={{ fontSize: 13, color: "#000", marginTop: 4, fontWeight: 600 }}>
              {card.label}
            </div>
          </div>
        ))}
      </div>
      <div
        className="nb-status-bar"
        style={{
          marginTop: 24,
          padding: "16px 20px",
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            background: adaptersOnline > 0 ? "#52c41a" : "#ff4d4f",
            border: "2px solid #000",
          }}
        />
        <span style={{ fontSize: 14, color: "#000", fontWeight: 700 }}>
          {t("dashboard.stats.adapters")}: {adaptersOnline}/{adaptersTotal}
        </span>
      </div>
    </div>
  );
}
