import { useTranslation } from "react-i18next";
import { Card, Typography } from "antd";

export default function Logs() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.logs_placeholder")}</Typography.Text>
    </Card>
  );
}
