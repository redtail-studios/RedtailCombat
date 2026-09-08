import { lazy, Suspense } from 'react';
import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { DashboardAuthProvider, useDashboardAuth } from '@/lib/DashboardAuthContext';
import { LoreReportsProvider } from '@/lib/LoreReportsContext';
import ScrollToTop from './components/ScrollToTop';
import Layout from '@/components/Layout';
import DashboardLayout from '@/components/dashboard/DashboardLayout';

// Route-level code splitting — each page (and its own dependencies, e.g.
// recharts/framer-motion) only downloads when its route is actually visited,
// instead of every page's code shipping in one ~1MB upfront bundle.
const Home = lazy(() => import('@/pages/Home'));
const Agents = lazy(() => import('@/pages/Agents'));
const Lore = lazy(() => import('@/pages/Lore'));
const Login = lazy(() => import('@/pages/Login'));
const Register = lazy(() => import('@/pages/Register'));
const ForgotPassword = lazy(() => import('@/pages/ForgotPassword'));
const ResetPassword = lazy(() => import('@/pages/ResetPassword'));
const MarketTrends = lazy(() => import('@/pages/dashboard/MarketTrends'));
const Portfolio = lazy(() => import('@/pages/dashboard/Portfolio'));
const Analyze = lazy(() => import('@/pages/dashboard/Analyze'));
const Reports = lazy(() => import('@/pages/dashboard/Reports'));
const DashboardPlaceholder = lazy(() => import('@/pages/dashboard/DashboardPlaceholder'));

const RouteFallback = () => (
  <div className="min-h-screen flex items-center justify-center bg-ink">
    <div className="w-6 h-6 border-2 border-white/10 border-t-pulse rounded-full animate-spin" />
  </div>
);

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
    <Suspense fallback={<RouteFallback />}>
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
    </Suspense>
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
