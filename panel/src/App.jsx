import AppRoutes from "./router";
import LanguageSelector from "./components/LanguageSelector";

export default function App() {
  return (
    <div style={{ position: "relative", minHeight: "100vh" }}>
      <AppRoutes />
    </div>
  );
}
