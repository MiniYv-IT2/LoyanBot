import { useTranslation } from "react-i18next";
import { Card, Typography } from "antd";

export default function GeneralSettings() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.settings.general_placeholder")}</Typography.Text>
    </Card>
  );
}
