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
    <ConfigProvider locale={locale}>
      <App />
    </ConfigProvider>
  );
}
