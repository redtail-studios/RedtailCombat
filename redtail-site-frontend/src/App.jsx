import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { DashboardAuthProvider, useDashboardAuth } from '@/lib/DashboardAuthContext';
import { LoreReportsProvider } from '@/lib/LoreReportsContext';
import ScrollToTop from './components/ScrollToTop';
import Layout from '@/components/Layout';
import Home from '@/pages/Home';
import Agents from '@/pages/Agents';
import Lore from '@/pages/Lore';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import MarketTrends from '@/pages/dashboard/MarketTrends';
import Portfolio from '@/pages/dashboard/Portfolio';
import Analyze from '@/pages/dashboard/Analyze';
import Reports from '@/pages/dashboard/Reports';
import DashboardPlaceholder from '@/pages/dashboard/DashboardPlaceholder';

const ProtectedDashboardRoute = ({ children }) => {
  const { isDashboardAuthenticated } = useDashboardAuth();
  if (!isDashboardAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const AuthenticatedApp = () => {
  // Home/Agents/Lore are public; /dashboard is gated by DashboardAuthProvider below.
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/lore" element={<Lore />} />
      </Route>
      <Route
        element={
          <ProtectedDashboardRoute>
            <DashboardLayout />
          </ProtectedDashboardRoute>
        }
      >
        <Route path="/dashboard" element={<MarketTrends />} />
        <Route path="/dashboard/portfolio" element={<Portfolio />} />
        <Route path="/dashboard/analyze" element={<Analyze />} />
        <Route path="/dashboard/updates" element={<DashboardPlaceholder title="Updates" />} />
        <Route path="/dashboard/reports" element={<Reports />} />
        <Route path="/dashboard/billing" element={<DashboardPlaceholder title="Billing" />} />
        <Route path="/dashboard/settings" element={<DashboardPlaceholder title="Settings" />} />
      </Route>
      <Route path="*" element={<PageNotFound />} />
    </Routes>
  );
};


function App() {

  return (
    <DashboardAuthProvider>
      <LoreReportsProvider>
        <QueryClientProvider client={queryClientInstance}>
          <Router>
            <ScrollToTop />
            <AuthenticatedApp />
          </Router>
          <Toaster />
        </QueryClientProvider>
      </LoreReportsProvider>
    </DashboardAuthProvider>
  )
}

export default App
