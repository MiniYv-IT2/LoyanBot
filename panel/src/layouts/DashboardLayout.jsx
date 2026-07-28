import { Drawer } from "antd";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import LanguageSelector from "../components/LanguageSelector";
import { useSidebar, SidebarProvider } from "../stores/useSidebarStore";

function LayoutInner() {
  const { mobileOpen, setMobileOpen } = useSidebar();

  return (
    <div className="nb-root">
      <div className="sidebar-desktop">
        <Sidebar />
      </div>

      <div className="topbar-mobile">
        <TopBar />
      </div>

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

        /* ─── Neobrutal Global ─── */
        .nb-root {
          min-height: 100vh;
          background: #fff;
          font-family: "Noto Sans SC", "Inter", -apple-system, sans-serif;
        }

        /* ─── Sidebar ─── */
        .sidebar-desktop {
          position: fixed;
          top: 0; left: 0; bottom: 0;
          width: 240px;
          background: #FFC2D1;
          z-index: 10;
          border-right: 3px solid #000;
        }

        /* Menu items as neobrutal buttons */
        .nb-sidebar .ant-menu {
          background: transparent !important;
          border: none !important;
          padding: 8px;
        }
        .nb-sidebar .ant-menu-item {
          background: #B8A1FF !important;
          border: 3px solid #000 !important;
          box-shadow: 4px 4px 0 #000 !important;
          margin-bottom: 8px !important;
          height: auto !important;
          line-height: 1.4 !important;
          padding: 12px 16px !important;
          border-radius: 0 !important;
          font-weight: 700 !important;
          font-size: 14px !important;
          color: #000 !important;
          transition: all 0.05s ease !important;
        }
        .nb-sidebar .ant-menu-item:hover {
          background: #a88fff !important;
          box-shadow: 3px 3px 0 #000 !important;
          transform: translate(1px, 1px) !important;
        }
        .nb-sidebar .ant-menu-item:active,
        .nb-sidebar .ant-menu-item-selected {
          background: #9a7fff !important;
          box-shadow: 1px 1px 0 #000 !important;
          transform: translate(3px, 3px) !important;
        }
        .nb-sidebar .ant-menu-item .ant-menu-item-icon {
          font-size: 18px !important;
          color: #000 !important;
        }
        .nb-sidebar .ant-menu-submenu {
          margin-bottom: 8px !important;
        }
        .nb-sidebar .ant-menu-submenu-title {
          background: #B8A1FF !important;
          border: 3px solid #000 !important;
          box-shadow: 4px 4px 0 #000 !important;
          height: auto !important;
          line-height: 1.4 !important;
          padding: 12px 16px !important;
          border-radius: 0 !important;
          font-weight: 700 !important;
          font-size: 14px !important;
          color: #000 !important;
          margin: 0 !important;
          transition: all 0.05s ease !important;
        }
        .nb-sidebar .ant-menu-submenu-title:hover {
          background: #a88fff !important;
          box-shadow: 3px 3px 0 #000 !important;
          transform: translate(1px, 1px) !important;
        }
        .nb-sidebar .ant-menu-submenu-open > .ant-menu-submenu-title {
          background: #a88fff !important;
          box-shadow: 2px 2px 0 #000 !important;
          transform: translate(2px, 2px) !important;
        }
        .nb-sidebar .ant-menu-submenu .ant-menu-item {
          margin-left: 12px !important;
          margin-top: 4px !important;
          margin-bottom: 4px !important;
          padding: 10px 16px !important;
          background: #fff !important;
          border: 2px solid #000 !important;
          box-shadow: 3px 3px 0 #000 !important;
        }
        .nb-sidebar .ant-menu-submenu .ant-menu-item:hover {
          background: #FFC2D1 !important;
          box-shadow: 2px 2px 0 #000 !important;
          transform: translate(1px, 1px) !important;
        }
        .nb-sidebar .ant-menu-submenu .ant-menu-item-selected {
          background: #FFC2D1 !important;
          box-shadow: 1px 1px 0 #000 !important;
          transform: translate(2px, 2px) !important;
        }
        .nb-sidebar .ant-menu-submenu-arrow {
          color: #000 !important;
        }
        .nb-sidebar .ant-menu-item-only-child {
          margin-left: 0 !important;
        }

        /* ─── Content Area ─── */
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
          border-bottom: 3px solid #000;
          background: #fff;
        }
        .content-body {
          flex: 1;
          padding: 24px;
          background: #fff;
        }

        /* ─── Neobrutal Card Overrides ─── */
        .nb-root .ant-card {
          border: 3px solid #000 !important;
          box-shadow: 5px 5px 0 #000 !important;
          border-radius: 0 !important;
        }
        .nb-root .ant-card-head {
          border-bottom: 3px solid #000 !important;
          background: #FFC2D1 !important;
          border-radius: 0 !important;
          font-weight: 700;
        }

        /* ─── Neobrutal Button Overrides ─── */
        .nb-root .ant-btn {
          border: 3px solid #000 !important;
          box-shadow: 4px 4px 0 #000 !important;
          border-radius: 0 !important;
          font-weight: 700 !important;
          height: 40px !important;
          transition: all 0.05s ease !important;
        }
        .nb-root .ant-btn:hover {
          transform: translate(-1px, -1px) !important;
          box-shadow: 5px 5px 0 #000 !important;
        }
        .nb-root .ant-btn:active {
          transform: translate(2px, 2px) !important;
          box-shadow: 2px 2px 0 #000 !important;
        }
        .nb-root .ant-btn-primary {
          background: #FF8FAB !important;
          border-color: #000 !important;
          color: #000 !important;
        }
        .nb-root .ant-btn-primary:hover {
          background: #ff7a9a !important;
        }
        .nb-root .ant-btn-default {
          background: #fff !important;
        }
        .nb-root .ant-btn-link {
          border: none !important;
          box-shadow: none !important;
          background: transparent !important;
        }

        /* ─── Table ─── */
        .nb-root .ant-table {
          border: 3px solid #000 !important;
          border-radius: 0 !important;
        }
        .nb-root .ant-table-thead > tr > th {
          background: #FFC2D1 !important;
          border-bottom: 3px solid #000 !important;
          color: #000 !important;
          font-weight: 700 !important;
          border-radius: 0 !important;
        }
        .nb-root .ant-table-tbody > tr > td {
          border-bottom: 2px solid #000 !important;
        }
        .nb-root .ant-table-tbody > tr:hover > td {
          background: #fff5f7 !important;
        }

        /* ─── Input / Select ─── */
        .nb-root .ant-input,
        .nb-root .ant-select-selector,
        .nb-root .ant-input-password {
          border: 3px solid #000 !important;
          border-radius: 0 !important;
          box-shadow: 3px 3px 0 #000 !important;
        }
        .nb-root .ant-input:focus,
        .nb-root .ant-select-focused .ant-select-selector {
          border-color: #FF8FAB !important;
          box-shadow: 3px 3px 0 #FF8FAB !important;
        }
        .nb-root .ant-input-affix-wrapper {
          border: 3px solid #000 !important;
          border-radius: 0 !important;
          box-shadow: 3px 3px 0 #000 !important;
          padding: 0 11px !important;
        }
        .nb-root .ant-input-affix-wrapper-focused {
          border-color: #FF8FAB !important;
          box-shadow: 3px 3px 0 #FF8FAB !important;
        }

        /* ─── Tag ─── */
        .nb-root .ant-tag {
          border: 2px solid #000 !important;
          border-radius: 0 !important;
          font-weight: 600 !important;
        }

        /* ─── Switch ─── */
        .nb-root .ant-switch {
          border: 2px solid #000 !important;
          border-radius: 0 !important;
          background: #fff !important;
        }
        .nb-root .ant-switch-checked {
          background: #B8A1FF !important;
        }

        /* ─── Modal ─── */
        .nb-root .ant-modal-content {
          border: 3px solid #000 !important;
          border-radius: 0 !important;
          box-shadow: 8px 8px 0 #000 !important;
        }
        .nb-root .ant-modal-header {
          border-radius: 0 !important;
          border-bottom: 3px solid #000 !important;
        }

        /* ─── Popover / Popconfirm ─── */
        .nb-root .ant-popover-inner {
          border: 3px solid #000 !important;
          border-radius: 0 !important;
          box-shadow: 4px 4px 0 #000 !important;
        }

        /* ─── Select Dropdown ─── */
        .nb-root .ant-select-dropdown {
          border: 3px solid #000 !important;
          border-radius: 0 !important;
          box-shadow: 4px 4px 0 #000 !important;
        }

        /* ─── Stat Cards (Dashboard Home) ─── */
        .nb-stat-card {
          background: #FFC2D1 !important;
          border: 3px solid #000 !important;
          box-shadow: 5px 5px 0 #000 !important;
          transition: all 0.05s ease !important;
        }
        .nb-stat-card:hover {
          transform: translate(-2px, -2px) !important;
          box-shadow: 7px 7px 0 #000 !important;
        }
        .nb-stat-card:nth-child(2) {
          background: #B8A1FF !important;
        }
        .nb-stat-card:nth-child(3) {
          background: #FF8FAB !important;
        }
        .nb-stat-card:nth-child(4) {
          background: #FFD700 !important;
        }

        /* ─── Adapter Status Bar ─── */
        .nb-status-bar {
          border: 3px solid #000 !important;
          box-shadow: 4px 4px 0 #000 !important;
          background: #fff !important;
        }

        /* ─── Logo Area ─── */
        .nb-logo {
          border-bottom: 3px solid #000 !important;
          padding: 16px !important;
          text-align: center;
          background: #FF8FAB;
        }

        /* ─── TopBar Mobile ─── */
        .topbar-mobile {
          display: none;
        }

        /* ─── Mobile ─── */
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
