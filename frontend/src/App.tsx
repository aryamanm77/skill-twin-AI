import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from '@/components/layout/Sidebar';
import { LoginPage } from '@/pages/LoginPage';
import { Dashboard } from '@/pages/Dashboard';
import { TrainingPage } from '@/pages/TrainingPage';
import { HistoryPage, SessionDetailPage } from '@/pages/HistoryPage';
import { useAuthStore } from '@/store';
import { useWebSocket } from '@/hooks/useWebSocket';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

// ── Layout wrapper (authenticated pages) ──────────────────────────────────────
function AppLayout() {
  useWebSocket();  // Initialize WebSocket connection

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto scrollbar-thin p-6 bg-grid">
        <Outlet />
      </main>
    </div>
  );
}

// ── Auth guard (bypassed) ──────────────────────────────────────────────────────
function RequireAuth() {
  return <Outlet />;
}

// ── Placeholder pages ──────────────────────────────────────────────────────────
function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-600">
      <div className="text-4xl">🚧</div>
      <div className="text-xl font-semibold text-slate-400">{title}</div>
      <div className="text-sm">Navigate to Training to use the main application</div>
    </div>
  );
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="training" element={<TrainingPage />} />
              <Route path="expert" element={<TrainingPage />} />
              <Route path="trainee" element={<TrainingPage />} />
              <Route path="twin" element={<PlaceholderPage title="Digital Twin (use Training page)" />} />
              <Route path="analytics" element={<PlaceholderPage title="Analytics — Coming in next phase" />} />
              <Route path="builder" element={<PlaceholderPage title="Procedure Builder — Coming in next phase" />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="history/:id" element={<SessionDetailPage />} />
              <Route path="settings" element={<PlaceholderPage title="Settings" />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
