import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import api from "../../api";
import logoSvg from "../../assets/images/Loyan.svg";

const BG = "#8ecac8";

export default function Dashboard() {
  const { t } = useTranslation();
  const [version, setVersion] = useState("");

  useEffect(() => {
    api.get("/api/loyanui/version").then((res) => {
      if (res.data.success) setVersion(res.data.data.version);
    }).catch(() => {});
  }, []);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <div
        style={{
          width: 220,
          background: "#fff",
          borderRight: "1px solid #f0f0f0",
          display: "flex",
          flexDirection: "column",
          padding: "20px 16px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <img
            src={logoSvg}
            alt="LoyanUI"
            style={{
              width: "clamp(36px, 5vw, 52px)",
              height: "clamp(36px, 5vw, 52px)",
              flexShrink: 0,
            }}
          />
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              lineHeight: "calc(clamp(36px, 5vw, 52px) / 2)",
            }}
          >
            <div
              style={{
                fontSize: "clamp(14px, 2vw, 18px)",
                fontWeight: 700,
                color: "#333",
                lineHeight: "inherit",
              }}
            >
              LoyanUI
            </div>
            <div
              style={{
                fontSize: "clamp(11px, 1.4vw, 13px)",
                color: "#999",
                lineHeight: "inherit",
              }}
            >
              v{version || "..."}
            </div>
          </div>
        </div>

        <div style={{ flex: 1 }} />

        <div style={{ fontSize: 12, color: "#ccc", textAlign: "center" }}>
          {t("app.title")} v{version || "..."}
        </div>
      </div>

      <div
        style={{
          flex: 1,
          background: `linear-gradient(135deg, ${BG}22, ${BG}11)`,
          padding: 24,
        }}
      >
        <h2 style={{ margin: 0, color: "#333", fontSize: "clamp(16px, 2.5vw, 24px)" }}>
          {t("dashboard.welcome")}
        </h2>
      </div>
    </div>
  );
}
