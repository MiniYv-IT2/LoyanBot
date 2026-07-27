import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Table, Button, Tag, Popconfirm, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import api from "../../../api";

export default function ProvidersList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = () => {
    setLoading(true);
    api.get("/api/loyanui/providers").then((res) => {
      setData(res.data || []);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleDelete = (id) => {
    api.delete(`/api/loyanui/providers/${id}`).then(() => {
      message.success(t("dashboard.deleted"));
      fetchData();
    }).catch(() => {});
  };

  const columns = [
    { title: t("dashboard.name"), dataIndex: "name", key: "name" },
    { title: t("dashboard.provider"), dataIndex: "provider", key: "provider" },
    {
      title: t("dashboard.status"),
      dataIndex: "status",
      key: "status",
      render: (status) => (
        <Tag color={status === "online" ? "green" : status === "offline" ? "red" : "default"}>
          {status || t("dashboard.unknown")}
        </Tag>
      ),
    },
    {
      title: t("dashboard.actions"),
      key: "actions",
      render: (_, record) => (
        <span>
          <Button type="link" onClick={() => navigate(`/providers/${record.id}/edit`)}>
            {t("dashboard.edit")}
          </Button>
          <Popconfirm title={t("dashboard.confirm_delete")} onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger>{t("dashboard.delete")}</Button>
          </Popconfirm>
        </span>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>{t("dashboard.sidebar.providers")}</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/providers/create")}>
          {t("dashboard.create")}
        </Button>
      </div>
      <Table rowKey="id" columns={columns} dataSource={data} loading={loading} />
    </div>
  );
}
