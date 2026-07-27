import { useTranslation } from "react-i18next";
import { Card, Row, Col, Tag } from "antd";
import { ToolOutlined } from "@ant-design/icons";

const TOOLS = [
  { name: "Translate", desc: "Translate text", plugin: "Translate" },
  { name: "WeatherQuery", desc: "Query weather", plugin: "Weather" },
  { name: "RunCode", desc: "Execute code", plugin: "CodeRunner" },
  { name: "GenerateImage", desc: "Generate image", plugin: "ImageGen" },
  { name: "WebSearch", desc: "Search the web", plugin: "Search" },
  { name: "SetReminder", desc: "Create reminder", plugin: "Reminder" },
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
                    <div>{tool.desc}</div>
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
