import { Select } from "antd";
import { GlobalOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

export default function LanguageSelector({ style }) {
  const { t, i18n } = useTranslation();

  const LANG_OPTIONS = [
    { value: "zh-CN", label: t("lang.zh") },
    { value: "en-US", label: t("lang.en") },
    { value: "ru-RU", label: t("lang.ru") },
  ];

  const handleChange = (value) => {
    i18n.changeLanguage(value);
  };

  return (
    <Select
      value={LANG_OPTIONS.some(o => o.value === i18n.language) ? i18n.language : "zh-CN"}
      onChange={handleChange}
      options={LANG_OPTIONS}
      suffixIcon={<GlobalOutlined />}
      bordered={false}
      style={{ width: 120, fontSize: 16, ...style }}
    />
  );
}
