import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

const BG = "var(--primary)";

function formatUptime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function DashboardHome() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch("/api/loyanui/stats")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setStats(res.data);
      })
      .catch(() => {});
  }, []);

  const cards = [
    { label: t("dashboard.stats.messages"), value: stats?.total_messages ?? "--" },
    { label: t("dashboard.stats.commands"), value: stats?.total_commands ?? "--" },
    { label: t("dashboard.stats.uptime"), value: stats ? formatUptime(stats.uptime_seconds) : "--" },
    { label: t("dashboard.stats.plugins"), value: stats?.plugins ?? "--" },
    {
      label: t("dashboard.stats.instances"),
      value: stats?.instances_enabled ?? "--",
    },
  ];

  return (
    <div>
      <h2 style={{ margin: "0 0 24px", color: "var(--text)", fontSize: 22 }}>
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
            key={card.label}
            style={{
              background: "#fafafa",
              border: "1px solid #f0f0f0",
              borderRadius: 8,
              padding: "20px 16px",
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700, color: BG }}>
              {card.value}
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
              {card.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
