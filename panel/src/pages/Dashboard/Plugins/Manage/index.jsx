import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Table, Switch, Button, Popconfirm, message, Tag } from "antd";

const INSTALLED = [
  { name: "Translate", version: "1.2.0", enabled: true, categoryKey: "dashboard.plugins.cat_utility" },
  { name: "Weather", version: "0.9.0", enabled: false, categoryKey: "dashboard.plugins.cat_utility" },
  { name: "CodeRunner", version: "2.1.0", enabled: true, categoryKey: "dashboard.plugins.cat_developer" },
];

export default function PluginManage() {
  const { t } = useTranslation();
  const [data, setData] = useState(INSTALLED);

  const toggleEnabled = (name) => {
    setData((prev) =>
      prev.map((p) => (p.name === name ? { ...p, enabled: !p.enabled } : p))
    );
  };

  const handleUninstall = (name) => {
    setData((prev) => prev.filter((p) => p.name !== name));
    message.success(t("dashboard.plugins.uninstalled"));
  };

  const columns = [
    { title: t("dashboard.name"), dataIndex: "name", key: "name" },
    { title: t("dashboard.plugins.version"), dataIndex: "version", key: "version" },
    {
      title: t("dashboard.plugins.category"),
      dataIndex: "category",
      key: "category",
      render: (_, record) => <Tag>{t(record.categoryKey)}</Tag>,
    },
    {
      title: t("dashboard.plugins.enabled"),
      dataIndex: "enabled",
      key: "enabled",
      render: (enabled, record) => (
        <Switch checked={enabled} onChange={() => toggleEnabled(record.name)} />
      ),
    },
    {
      title: t("dashboard.actions"),
      key: "actions",
      render: (_, record) => (
        <Popconfirm
          title={t("dashboard.plugins.confirm_uninstall")}
          onConfirm={() => handleUninstall(record.name)}
        >
          <Button type="link" danger>{t("dashboard.plugins.uninstall")}</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ margin: "0 0 16px" }}>{t("dashboard.plugins.manage")}</h2>
      <Table rowKey="name" columns={columns} dataSource={data} />
    </div>
  );
}
