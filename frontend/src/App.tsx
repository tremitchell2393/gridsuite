/**
 * App — top-level routing.
 *
 * Wraps everything in QueryClientProvider (React Query) and
 * AuthProvider. Authenticated routes are nested under AppLayout
 * (sidebar/topbar shell); unauthenticated users are redirected to
 * /login via RequireAuth.
 */
import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { AppLayout } from "@/components/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { LaneDetailPage } from "@/pages/LaneDetailPage";
import { SignalLibraryPage } from "@/pages/SignalLibraryPage";
import { AlertsPage } from "@/pages/AlertsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { LoginPage } from "@/pages/LoginPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route
              path="/"
              element={
                <RequireAuth>
                  <AppLayout />
                </RequireAuth>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="lanes/:laneId" element={<LaneDetailPage />} />
              <Route path="signals" element={<SignalLibraryPage />} />
              <Route path="alerts" element={<AlertsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
