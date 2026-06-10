import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function useLiveEvents(agentId: string) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!agentId) {
      setConnected(false);
      return;
    }
    const source = new EventSource(
      `/api/v1/agents/${encodeURIComponent(agentId)}/events/stream`,
    );
    const refresh = () => {
      void queryClient.invalidateQueries({
        queryKey: ["interception", agentId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["session", agentId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["sessions", agentId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["memory", agentId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["operations", agentId],
      });
    };
    source.onopen = () => {
      setConnected(true);
      refresh();
    };
    source.onmessage = refresh;
    source.onerror = () => setConnected(false);
    for (const event of [
      "state",
      "live_event",
      "interception_paused",
      "approval_resolved",
      "approval.pending",
      "approval.resolved",
    ]) {
      source.addEventListener(event, refresh);
    }
    return () => {
      source.close();
      setConnected(false);
    };
  }, [agentId, queryClient]);

  return connected;
}
