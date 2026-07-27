import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu } from "antd";
import {
  HomeOutlined,
  ApiOutlined,
  CloudOutlined,
  RobotOutlined,
  ToolOutlined,
  BookOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  SettingOutlined,
  SkinOutlined,
} from "@ant-design/icons";
import { useSidebar } from "../stores/useSidebarStore";
import LogoArea from "./LogoArea";

function getItem(label, key, icon, children) {
  return { key, icon, children, label };
}

const menuItems = (t) => [
  getItem(t("dashboard.sidebar.home"), "/", <HomeOutlined />),
  getItem(t("dashboard.sidebar.adapters"), "/adapters", <ApiOutlined />),
  getItem(t("dashboard.sidebar.providers"), "/providers", <CloudOutlined />),
  getItem(t("dashboard.sidebar.ai_tools"), "/ai-tools", <RobotOutlined />, [
    getItem(t("dashboard.sidebar.mcp"), "/ai-tools/mcp", <ToolOutlined />),
    getItem(t("dashboard.sidebar.knowledge"), "/ai-tools/knowledge", <BookOutlined />),
    getItem(t("dashboard.sidebar.memory"), "/ai-tools/memory", <DatabaseOutlined />),
    getItem(t("dashboard.sidebar.agent"), "/ai-tools/agent", <ExperimentOutlined />),
    getItem(t("dashboard.sidebar.skill"), "/ai-tools/skill", <ThunderboltOutlined />),
  ]),
  getItem(t("dashboard.sidebar.logs"), "/logs", <FileTextOutlined />),
  getItem(t("dashboard.sidebar.settings"), "/settings", <SettingOutlined />, [
    getItem(t("dashboard.sidebar.ai_settings"), "/settings/ai", <RobotOutlined />),
    getItem(t("dashboard.sidebar.general"), "/settings/general", <SkinOutlined />),
  ]),
];

export default function Sidebar({ mobile = false, onClose }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { collapsed } = useSidebar();

  const onClick = ({ key }) => {
    navigate(key);
    if (mobile && onClose) onClose();
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: "#fff",
        borderRight: "1px solid #f0f0f0",
      }}
    >
      <LogoArea collapsed={collapsed} />
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        defaultOpenKeys={["/ai-tools", "/settings"]}
        items={menuItems(t)}
        onClick={onClick}
        inlineCollapsed={collapsed}
        style={{ borderRight: "none", flex: 1 }}
      />
    </div>
  );
}
