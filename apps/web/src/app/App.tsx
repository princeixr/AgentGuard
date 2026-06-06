import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { LoadingState } from "../components/LoadingState";
import { DEMO_AGENT_ID } from "../config/demo";

const LiveInterceptionPage = lazy(() =>
  import("../features/live/LiveInterceptionPage").then((module) => ({
    default: module.LiveInterceptionPage,
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
const TraceReplayPage = lazy(() =>
  import("../features/replay/TraceReplayPage").then((module) => ({
    default: module.TraceReplayPage,
  })),
);
const DecisionMemoryPage = lazy(() =>
  import("../features/memory/DecisionMemoryPage").then((module) => ({
    default: module.DecisionMemoryPage,
  })),
);
const OperationsPage = lazy(() =>
  import("../features/operations/OperationsPage").then((module) => ({
    default: module.OperationsPage,
  })),
);

export function App() {
  return (
    <Suspense fallback={<LoadingState label="Loading AgentGuard" />}>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate replace to="/agents" />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:agentId" element={<AgentDetailPage />} />
          <Route
            path="/live"
            element={
              <Navigate replace to={`/agents/${DEMO_AGENT_ID}/live`} />
            }
          />
          <Route
            path="/replay"
            element={
              <Navigate replace to={`/agents/${DEMO_AGENT_ID}/replay`} />
            }
          />
          <Route
            path="/memory"
            element={
              <Navigate replace to={`/agents/${DEMO_AGENT_ID}/memory`} />
            }
          />
          <Route
            path="/operations"
            element={
              <Navigate replace to={`/agents/${DEMO_AGENT_ID}/operations`} />
            }
          />
          <Route
            path="/agents/:agentId/live"
            element={<LiveInterceptionPage />}
          />
          <Route
            path="/agents/:agentId/replay"
            element={<TraceReplayPage />}
          />
          <Route
            path="/agents/:agentId/memory"
            element={<DecisionMemoryPage />}
          />
          <Route
            path="/agents/:agentId/operations"
            element={<OperationsPage />}
          />
        </Route>
      </Routes>
    </Suspense>
  );
}
