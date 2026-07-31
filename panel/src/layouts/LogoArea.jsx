import { useTranslation } from "react-i18next";
import logoSvg from "../assets/images/Loyan.svg";

export default function LogoArea({ collapsed }) {
  const { t } = useTranslation();
  if (collapsed) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: 64,
          padding: "12px 0",
        }}
      >
        <img
          src={logoSvg}
          alt="LoyanUI"
          style={{ width: 32, height: 32 }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "16px 20px",
        borderBottom: "1px solid #f0f0f0",
      }}
    >
      <img
        src={logoSvg}
        alt="LoyanUI"
        style={{
          width: "clamp(36px, 4vw, 48px)",
          height: "clamp(36px, 4vw, 48px)",
          flexShrink: 0,
        }}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          lineHeight: "calc(clamp(36px, 4vw, 48px) / 2)",
        }}
      >
        <div
          style={{
            fontSize: "clamp(14px, 1.8vw, 17px)",
            fontWeight: 700,
            color: "var(--text)",
            lineHeight: "inherit",
          }}
        >
          {t("app.title")}
        </div>
        <div
          style={{
            fontSize: "clamp(11px, 1.2vw, 13px)",
            color: "var(--text-secondary)",
            lineHeight: "inherit",
          }}
        >
          {t("app.version")}
        </div>
      </div>
    </div>
  );
}
