import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

export function useLiveEvents(agentId: string) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const source = new EventSource(
      `/api/v1/agents/${encodeURIComponent(agentId)}/events/stream`,
    );
    const refresh = () => {
      void queryClient.invalidateQueries({
        queryKey: ["interception", agentId],
      });
    };
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    for (const event of [
      "state",
      "live_event",
      "interception_paused",
      "approval_resolved",
      "scenario_completed",
      "demo_reset",
    ]) {
      source.addEventListener(event, refresh);
    }
    return () => source.close();
  }, [agentId, queryClient]);

  return connected;
}
