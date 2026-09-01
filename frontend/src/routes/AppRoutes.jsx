import { Navigate, Route, Routes } from "react-router-dom";

import AuditPage from "../pages/AuditPage";
import BotPage from "../pages/BotPage";
import DashboardPage from "../pages/DashboardPage";
import EvidencePage from "../pages/EvidencePage";
import ReportsPage from "../pages/ReportsPage";
import WebsiteConfigPage from "../pages/WebsiteConfigPage";

export default function AppRoutes() {
  return (
    <Routes>

      <Route
        path="/"
        element={<Navigate to="/dashboard" replace />}
      />

      <Route
        path="/dashboard"
        element={<DashboardPage />}
      />

      <Route
        path="/website-config"
        element={<WebsiteConfigPage />}
      />

      <Route
        path="/audits"
        element={<AuditPage />}
      />

      <Route
        path="/evidence"
        element={<EvidencePage />}
      />

      <Route
        path="/reports"
        element={<ReportsPage />}
      />

      <Route
        path="/bot"
        element={<BotPage />}
      />

    </Routes>
  );
}