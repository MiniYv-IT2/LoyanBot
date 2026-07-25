import { useTranslation } from "react-i18next";

export default function Dashboard() {
  const { t } = useTranslation();
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        color: "#333",
        fontSize: 24,
      }}
    >
      {t("app.title")} — {t("app.subtitle")}
    </div>
  );
}
