import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DatasetsPage from "./pages/DatasetsPage";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import FindingsPage from "./pages/FindingsPage";
import ColumnsPage from "./pages/ColumnsPage";
import TrendPage from "./pages/TrendPage";
import ComparePage from "./pages/ComparePage";
import PublicReportPage from "./pages/PublicReportPage";
import AlertsPage from "./pages/AlertsPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/public/reports/:token" element={<PublicReportPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<DatasetsPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/datasets/:datasetId" element={<DashboardPage />} />
              <Route path="/datasets/:datasetId/findings" element={<FindingsPage />} />
              <Route path="/datasets/:datasetId/columns" element={<ColumnsPage />} />
              <Route path="/datasets/:datasetId/trend" element={<TrendPage />} />
              <Route path="/datasets/:datasetId/compare" element={<ComparePage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
