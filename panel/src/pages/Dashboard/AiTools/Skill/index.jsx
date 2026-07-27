import { useTranslation } from "react-i18next";
import { Card, Typography } from "antd";

export default function Skill() {
  const { t } = useTranslation();
  return (
    <Card>
      <Typography.Text type="secondary">{t("dashboard.ai_tools.skill_placeholder")}</Typography.Text>
    </Card>
  );
}
