import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Input, Card, Button, Row, Col, Tag, message } from "antd";
import { SearchOutlined } from "@ant-design/icons";

const PLUGINS = [
  { name: "Translate", desc: "Translate text between languages", icon: "🌐", category: "utility" },
  { name: "Weather", desc: "Get weather forecasts", icon: "☀️", category: "utility" },
  { name: "CodeRunner", desc: "Run code snippets in various languages", icon: "💻", category: "developer" },
  { name: "ImageGen", desc: "Generate images from text prompts", icon: "🎨", category: "media" },
  { name: "Search", desc: "Web search integration", icon: "🔍", category: "utility" },
  { name: "Reminder", desc: "Set and manage reminders", icon: "⏰", category: "utility" },
];

export default function PluginMarket() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");

  const filtered = PLUGINS.filter(
    (p) => p.name.toLowerCase().includes(search.toLowerCase()) || p.desc.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.plugins.market")}</h2>
      <Input
        prefix={<SearchOutlined />}
        placeholder={t("dashboard.plugins.search_placeholder")}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ marginBottom: 16, maxWidth: 400 }}
      />
      <Row gutter={[16, 16]}>
        {filtered.map((plugin) => (
          <Col key={plugin.name} xs={24} sm={12} md={8} lg={6}>
            <Card
              hoverable
              actions={[
                <Button type="primary" size="small" onClick={() => message.success(t("dashboard.plugins.installed"))}>
                  {t("dashboard.plugins.install")}
                </Button>,
              ]}
            >
              <Card.Meta
                avatar={<span style={{ fontSize: 28 }}>{plugin.icon}</span>}
                title={plugin.name}
                description={
                  <>
                    <div>{plugin.desc}</div>
                    <Tag style={{ marginTop: 8 }}>{plugin.category}</Tag>
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
