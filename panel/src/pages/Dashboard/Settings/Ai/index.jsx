import { useTranslation } from "react-i18next";
import { Card, Typography } from "antd";

export default function AiSettings() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.settings.ai_placeholder")}</Typography.Text>
    </Card>
  );
}
