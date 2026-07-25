import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import { verifyToken } from "./api";
import LanguageSelector from "./components/LanguageSelector";

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

export default function App() {
  return (
    <div style={{ position: "relative", minHeight: "100vh" }}>
      <div style={{ position: "fixed", top: 16, right: 16, zIndex: 1000 }}>
        <LanguageSelector />
      </div>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </div>
  );
}
