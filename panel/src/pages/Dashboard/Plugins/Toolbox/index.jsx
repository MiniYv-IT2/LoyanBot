import { useTranslation } from "react-i18next";
import { Card, Row, Col, Tag } from "antd";
import { ToolOutlined } from "@ant-design/icons";

const TOOLS = [
  { name: "Translate", descKey: "dashboard.plugins.desc_translate_tool", plugin: "Translate" },
  { name: "WeatherQuery", descKey: "dashboard.plugins.desc_weather_tool", plugin: "Weather" },
  { name: "RunCode", descKey: "dashboard.plugins.desc_coderunner_tool", plugin: "CodeRunner" },
  { name: "GenerateImage", descKey: "dashboard.plugins.desc_imagegen_tool", plugin: "ImageGen" },
  { name: "WebSearch", descKey: "dashboard.plugins.desc_search_tool", plugin: "Search" },
  { name: "SetReminder", descKey: "dashboard.plugins.desc_reminder_tool", plugin: "Reminder" },
];

export default function PluginToolbox() {
  const { t } = useTranslation();

  return (
    <div>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.plugins.toolbox")}</h2>
      <Row gutter={[16, 16]}>
        {TOOLS.map((tool) => (
          <Col key={tool.name} xs={24} sm={12} md={8} lg={6}>
            <Card hoverable>
              <Card.Meta
                avatar={<ToolOutlined style={{ fontSize: 24, color: "#8ecac8" }} />}
                title={tool.name}
                description={
                  <>
                    <div>{t(tool.descKey)}</div>
                    <Tag style={{ marginTop: 8 }}>{tool.plugin}</Tag>
                  </>
                }
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
