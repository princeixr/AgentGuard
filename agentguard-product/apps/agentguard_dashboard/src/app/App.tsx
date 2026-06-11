import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { AdminPage } from "../features/admin/AdminPage";
import { LivePage } from "../features/live/LivePage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { TraceDetailPage } from "../features/traces/TraceDetailPage";
import { TracesPage } from "../features/traces/TracesPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate replace to="/overview" />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/live" element={<LivePage />} />
        <Route path="/traces" element={<TracesPage />} />
        <Route path="/traces/:id" element={<TraceDetailPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="*" element={<Navigate replace to="/overview" />} />
      </Route>
    </Routes>
  );
}
