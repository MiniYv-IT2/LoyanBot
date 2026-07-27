import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import AppWrapper from "./AppWrapper";
import "./i18n";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppWrapper />
    </BrowserRouter>
  </React.StrictMode>
);

// 全局样式：防止移动端点击表单元素时自动缩放
const style = document.createElement("style");
style.textContent = "select,input,textarea,button,.ant-select,.ant-select-selector{font-size:16px!important}";
document.head.appendChild(style);
