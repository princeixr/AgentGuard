import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { LoadingState } from "../components/LoadingState";

const LiveInterceptionPage = lazy(() =>
  import("../features/live/LiveInterceptionPage").then((module) => ({
    default: module.LiveInterceptionPage,
  })),
);
const SessionHistoryPage = lazy(() =>
  import("../features/sessions/SessionHistoryPage").then((module) => ({
    default: module.SessionHistoryPage,
  })),
);
const SecuritySummaryPage = lazy(() =>
  import("../features/summary/SecuritySummaryPage").then((module) => ({
    default: module.SecuritySummaryPage,
  })),
);
const AgentsPage = lazy(() =>
  import("../features/agents/AgentsPage").then((module) => ({
    default: module.AgentsPage,
  })),
);
const AgentDetailPage = lazy(() =>
  import("../features/agents/AgentDetailPage").then((module) => ({
    default: module.AgentDetailPage,
  })),
);
const GuardAdminPage = lazy(() =>
  import("../features/guard/GuardAdminPage").then((module) => ({
    default: module.GuardAdminPage,
  })),
);

export function App() {
  return (
    <Suspense fallback={<LoadingState label="Loading AgentGuard" />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate replace to="/agents" />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/approvals" element={<Navigate replace to="/agents" />} />
          <Route path="/agents/:agentId" element={<AgentDetailPage />} />
          <Route path="/live" element={<Navigate replace to="/agents" />} />
          <Route path="/replay" element={<Navigate replace to="/agents" />} />
          <Route path="/memory" element={<Navigate replace to="/agents" />} />
          <Route path="/operations" element={<Navigate replace to="/agents" />} />
          <Route path="/sessions" element={<Navigate replace to="/agents" />} />
          <Route path="/summary" element={<Navigate replace to="/agents" />} />
          <Route
            path="/agents/:agentId/live"
            element={<Navigate replace to="../trace-interception" />}
          />
          <Route
            path="/agents/:agentId/trace-interception"
            element={<LiveInterceptionPage />}
          />
          <Route
            path="/agents/:agentId/sessions"
            element={<SessionHistoryPage />}
          />
          <Route
            path="/agents/:agentId/summary"
            element={<SecuritySummaryPage />}
          />
          <Route
            path="/agents/:agentId/replay"
            element={<Navigate replace to="../trace-interception" />}
          />
          <Route
            path="/agents/:agentId/memory"
            element={<Navigate replace to="../trace-interception" />}
          />
          <Route
            path="/agents/:agentId/operations"
            element={<Navigate replace to="../summary" />}
          />
          <Route
            path="/agents/:agentId/guard"
            element={<GuardAdminPage />}
          />
        </Route>
      </Routes>
    </Suspense>
  );
}
