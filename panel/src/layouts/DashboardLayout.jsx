import { Drawer } from "antd";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import LanguageSelector from "../components/LanguageSelector";
import { useSidebar, SidebarProvider } from "../stores/useSidebarStore";

function LayoutInner() {
  const { mobileOpen, setMobileOpen } = useSidebar();

  return (
    <div style={{ minHeight: "100vh", background: "#fff" }}>
      {/* 桌面侧边栏 */}
      <div className="sidebar-desktop">
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
        styles={{ body: { padding: 0 } }}
        mask={false}
      >
        <Sidebar mobile onClose={() => setMobileOpen(false)} />
      </Drawer>

      {/* 内容区 */}
      <div className="content-area">
        <div className="content-header">
          <LanguageSelector />
        </div>
        <div className="content-body">
          <Outlet />
        </div>
      </div>

      <style>{`
        select, input, textarea, button, .ant-select { font-size: 16px !important; }

        .sidebar-desktop {
          position: fixed;
          top: 0; left: 0; bottom: 0;
          width: 240px;
          background: #fff;
          z-index: 10;
        }
        .content-area {
          margin-left: 240px;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }
        .content-header {
          display: flex;
          justify-content: flex-end;
          align-items: center;
          padding: 12px 24px;
          border-bottom: 1px solid #f0f0f0;
        }
        .content-body {
          flex: 1;
          padding: 24px;
        }
        .topbar-mobile { display: none; }

        @media (max-width: 768px) {
          .sidebar-desktop { display: none; }
          .content-area { margin-left: 0; width: 100%; }
          .content-header { display: none; }
          .content-body { padding: 16px; }
          .topbar-mobile { display: flex; }
        }
      `}</style>
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
