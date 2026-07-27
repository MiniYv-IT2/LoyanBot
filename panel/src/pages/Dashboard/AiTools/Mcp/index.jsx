import { useTranslation } from "react-i18next";
import { Card, Typography } from "antd";

export default function Mcp() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.ai_tools.mcp_placeholder")}</Typography.Text>
    </Card>
  );
}
