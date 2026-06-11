import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

export function useProductionAgent() {
  const agents = useQuery({
    queryKey: ["agents"],
    queryFn: api.agents,
    refetchInterval: 10_000,
  });
  const productionAgents =
    agents.data?.items.filter(
      (item) => item.metadata.registration_source !== "demo_fixture",
    ) ?? [];
  const agent = productionAgents.find((item) => item.status === "live") ??
    productionAgents[0];

  return {
    agents,
    productionAgents,
    agent,
    agentId: agent?.agent_id ?? "",
  };
}
