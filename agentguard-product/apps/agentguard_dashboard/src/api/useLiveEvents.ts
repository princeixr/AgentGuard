import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getApiKey } from "./client";

export function useLiveEvents(agentId: string) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams();
    const apiKey = getApiKey();
    if (apiKey) params.set("access_token", apiKey);
    const source = new EventSource(
      `/api/v1/agents/${encodeURIComponent(agentId)}/events/stream?${params.toString()}`,
    );
    const refresh = () => {
      void queryClient.invalidateQueries({
        queryKey: ["interception", agentId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["session", agentId],
      });
    };
    source.onopen = () => setConnected(true);
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
    return () => source.close();
  }, [agentId, queryClient]);

  return connected;
}
