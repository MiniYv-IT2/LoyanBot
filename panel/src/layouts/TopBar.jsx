import { MenuOutlined } from "@ant-design/icons";
import LanguageSelector from "../components/LanguageSelector";
import { useSidebar } from "../stores/useSidebarStore";

export default function TopBar() {
  const { setMobileOpen } = useSidebar();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        height: 56,
        background: "#fff",
        borderBottom: "1px solid #f0f0f0",
        width: "100%",
      }}
    >
      <MenuOutlined
        style={{ fontSize: 20, cursor: "pointer" }}
        onClick={() => setMobileOpen(true)}
      />
      <LanguageSelector />
    </div>
  );
}
