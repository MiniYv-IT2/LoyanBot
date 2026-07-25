import { Select } from "antd";
import { GlobalOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

const LANG_OPTIONS = [
  { value: "zh-CN", label: "简体中文" },
  { value: "en-US", label: "English" },
  { value: "ru-RU", label: "Русский" },
];

export default function LanguageSelector({ style }) {
  const { i18n } = useTranslation();

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
      style={{ width: 120, ...style }}
    />
  );
}
