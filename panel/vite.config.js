import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    cors: true,
    allowedHosts: "all",
    proxy: {
      "/api": {
        target: "http://localhost:5090",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../loyan/panel-dist"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/node_modules\/(react|react-dom|react-router-dom|react-is|scheduler)\//.test(id)) return "react";
          if (/node_modules\/(antd|@ant-design\/icons|@ant-design\/v5-patch-for-react-19|@ant-design\/cssinjs|@rc-component|rc-)/.test(id)) return "antd";
          if (id.includes("node_modules/@ant-design/x")) return "antx";
          if (/node_modules\/(react-markdown|remark-|rehype-|react-syntax-highlighter|unified|micromark|hast|mdast|vfile|lowlight|refractor|parse5|property-information|character-entities|comma-separated-tokens|decode-named-character-reference|devlop|zwitch|trim-lines|unist-|web-namespaces|html-void-elements|ccount|longest-streak|markdown-table)/.test(id)) return "markdown";
          return undefined;
        },
      },
    },
  },
});
