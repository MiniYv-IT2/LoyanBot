import { Card, Typography } from "antd";
import { useTranslation } from "react-i18next";

export default function Settings() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.settings_placeholder")}</Typography.Text>
    </Card>
  );
}
