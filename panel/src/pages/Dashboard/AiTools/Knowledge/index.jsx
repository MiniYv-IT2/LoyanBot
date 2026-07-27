import { useTranslation } from "react-i18next";
import { Card, Typography } from "antd";

export default function Knowledge() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.ai_tools.knowledge_placeholder")}</Typography.Text>
    </Card>
  );
}
