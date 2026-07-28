import { useState, useEffect } from "react";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import ruRU from "antd/locale/ru_RU";
import i18n from "./i18n";
import App from "./App";

const LOCALE_MAP = {
  "zh-CN": zhCN,
  "en-US": enUS,
  "ru-RU": ruRU,
};

const theme = {
  token: {
    colorPrimary: "#FF8FAB",
    colorInfo: "#FF8FAB",
    colorSuccess: "#52c41a",
    colorWarning: "#faad14",
    colorError: "#ff4d4f",
    colorBorder: "#000",
    borderRadius: 0,
    borderRadiusLG: 0,
    borderRadiusSM: 0,
    colorBgContainer: "#fff",
    boxShadow: "4px 4px 0px 0px rgba(0,0,0,1)",
    boxShadowSecondary: "6px 6px 0px 0px rgba(0,0,0,1)",
    fontFamily: '"Noto Sans SC", "Inter", -apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: 14,
    fontWeightStrong: 700,
  },
  components: {
    Button: {
      borderRadius: 0,
      controlHeight: 40,
      fontSize: 14,
      fontWeight: 700,
      borderColorDisabled: "#000",
      colorBorder: "#000",
      defaultBorderColor: "#000",
      primaryShadow: "3px 3px 0px 0px rgba(0,0,0,1)",
      defaultShadow: "3px 3px 0px 0px rgba(0,0,0,1)",
    },
    Card: {
      borderRadius: 0,
      colorBorderSecondary: "#000",
    },
    Table: {
      borderRadius: 0,
      borderColor: "#000",
      headerBg: "#FFC2D1",
      headerColor: "#000",
    },
    Menu: {
      borderRadius: 0,
      itemBorderRadius: 0,
      activeBarBorderWidth: 0,
      subMenuItemBg: "transparent",
      itemBg: "#B8A1FF",
      itemColor: "#000",
    },
    Input: {
      borderRadius: 0,
      colorBorder: "#000",
      activeBorderColor: "#FF8FAB",
      activeShadow: "2px 2px 0px 0px rgba(0,0,0,1)",
    },
    Select: {
      borderRadius: 0,
      colorBorder: "#000",
      optionFontSize: 14,
    },
    Modal: {
      borderRadius: 0,
      contentBg: "#fff",
      headerBg: "#fff",
    },
    Tag: {
      borderRadius: 0,
      colorBorder: "#000",
    },
    Switch: {
      borderRadius: 0,
      trackPadding: 0,
    },
    Popconfirm: {
      borderRadius: 0,
    },
    Tabs: {
      borderRadius: 0,
    },
    Drawer: {
      borderRadius: 0,
    },
    Notification: {
      borderRadius: 0,
    },
    Message: {
      borderRadius: 0,
    },
  },
};

export default function AppWrapper() {
  const [locale, setLocale] = useState(LOCALE_MAP[i18n.language] || zhCN);

  useEffect(() => {
    const handleLang = (lng) => {
      setLocale(LOCALE_MAP[lng] || zhCN);
    };
    i18n.on("languageChanged", handleLang);
    return () => i18n.off("languageChanged", handleLang);
  }, []);

  return (
    <ConfigProvider locale={locale} theme={theme}>
      <App />
    </ConfigProvider>
  );
}
