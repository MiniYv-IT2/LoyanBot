import { Drawer } from "antd";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import LanguageSelector from "../components/LanguageSelector";
import ThemeSelector from "../components/ThemeSelector";
import UpdateChecker from "../components/UpdateChecker";
import { useSidebar, SidebarProvider } from "../stores/useSidebarStore";
import "../styles/global.css";
import "../styles/themes.css";

function LayoutInner() {
  const { mobileOpen, setMobileOpen, collapsed, setCollapsed } = useSidebar();

  return (
    <div className="app-container">
      {/* 桌面侧边栏 */}
      <div className={`sidebar-desktop${collapsed ? ' collapsed' : ''}`}>
        <Sidebar />
      </div>

      {/* 手机顶栏 */}
      <div className="topbar-mobile">
        <TopBar />
      </div>

      {/* 手机 Drawer */}
      <Drawer
        placement="left"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        width={260}
        styles={{ body: { padding: 0, background: `linear-gradient(180deg, var(--bg-start) 0%, var(--bg-mid) 15%, var(--bg-end) 40%, #fff 60%)` } }}
        mask={false}
      >
        <Sidebar mobile onClose={() => setMobileOpen(false)} />
      </Drawer>

      {/* 内容区 */}
      <div className="content-area">
        <div className="content-header">
          <UpdateChecker />
          <ThemeSelector />
          <LanguageSelector />
        </div>
        <div className="content-body">
          <Outlet />
        </div>
      </div>

    </div>
  );
}

export default function DashboardLayout() {
  return (
    <SidebarProvider>
      <LayoutInner />
    </SidebarProvider>
  );
}
