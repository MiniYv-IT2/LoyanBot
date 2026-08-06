import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Login from "../pages/Login";
import DashboardLayout from "../layouts/DashboardLayout";
import DashboardHome from "../pages/Dashboard/Home";
import AdaptersList from "../pages/Dashboard/Adapters";
import AdapterCreate from "../pages/Dashboard/Adapters/Create";

import ProvidersList from "../pages/Dashboard/Providers";
import ProviderCreate from "../pages/Dashboard/Providers/Create";
import ProviderEdit from "../pages/Dashboard/Providers/[id]/Edit";
import ChatPage from "../pages/Dashboard/Chat";
import AiTools from "../pages/Dashboard/AiTools";
import Mcp from "../pages/Dashboard/AiTools/Mcp";
import Knowledge from "../pages/Dashboard/AiTools/Knowledge";
import Memory from "../pages/Dashboard/AiTools/Memory";
import Agent from "../pages/Dashboard/AiTools/Agent";
import Skill from "../pages/Dashboard/AiTools/Skill";
import Logs from "../pages/Dashboard/Logs";
import PluginStore from "../pages/Dashboard/Plugins/Store";
import PluginManage from "../pages/Dashboard/Plugins/Manage";
import Settings from "../pages/Dashboard/Settings";
import AiSettings from "../pages/Dashboard/Settings/Ai";
import GeneralSettings from "../pages/Dashboard/Settings/General";
import NotFound from "../pages/NotFound";
import { verifyToken } from "../api";

function ProtectedRoute({ children }) {
  const [ok, setOk] = useState(null);
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return setOk(false);
    verifyToken(token)
      .then(() => setOk(true))
      .catch(() => {
        localStorage.removeItem("token");
        setOk(false);
      });
  }, []);
  if (ok === null) return null;
  return ok ? children : <Navigate to="/login" />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardHome />} />
        <Route path="adapters" element={<AdaptersList />} />
        <Route path="adapters/create" element={<AdapterCreate />} />
        <Route path="providers" element={<ProvidersList />} />
        <Route path="providers/create" element={<ProviderCreate />} />
        <Route path="providers/:id/edit" element={<ProviderEdit />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="plugins/store" element={<PluginStore />} />
        <Route path="plugins/manage" element={<PluginManage />} />
        <Route path="ai-tools" element={<AiTools />} />
        <Route path="ai-tools/mcp" element={<Mcp />} />
        <Route path="ai-tools/knowledge" element={<Knowledge />} />
        <Route path="ai-tools/memory" element={<Memory />} />
        <Route path="ai-tools/agent" element={<Agent />} />
        <Route path="ai-tools/skill" element={<Skill />} />
        <Route path="logs" element={<Logs />} />
        <Route path="settings" element={<Settings />} />
        <Route path="settings/ai" element={<AiSettings />} />
        <Route path="settings/general" element={<GeneralSettings />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
