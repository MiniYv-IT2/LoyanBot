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

const style = document.createElement("style");
style.textContent = [
  "select,input,textarea,button,.ant-select,.ant-select-selector{font-size:16px!important}",
  "body{margin:0;padding:0;background:#fff}",
  "*,*::before,*::after{box-sizing:border-box}",
  "::-webkit-scrollbar{width:8px}",
  "::-webkit-scrollbar-track{background:#fff;border-left:2px solid #000}",
  "::-webkit-scrollbar-thumb{background:#B8A1FF;border:2px solid #000}",
].join("");
document.head.appendChild(style);
