import { HouseholdPlannerAPI, type PlannerSummary } from "~/lib/api/user/household-planner";
import { useRequests } from "~/composables/api/api-client";
import type { PersonalOut, StateOut } from "~/lib/api/types/household-planner";

export function useHouseholdPlanner() {
  const api = new HouseholdPlannerAPI(useRequests());
  const data = ref<StateOut | null>(null);
  const personal = ref<PersonalOut | null>(null);
  const members = ref<{ id: string; name: string }[]>([]);
  const busy = ref(false);
  const error = ref("");
  async function run(action: () => Promise<void>) {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    try { await action(); }
    catch (e: unknown) {
      const failure = e as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail = failure.response?.data?.detail;
      error.value = typeof detail === "string" ? detail : failure.message || "Request failed. Reload and try again.";
    }
    finally { busy.value = false; }
  }
  async function refresh() {
    const [s, p, m] = await Promise.all([api.state(), api.personal(), api.read<{ id: string; name: string }[]>("/members")]);
    data.value = s;
    personal.value = p;
    members.value = m;
  }
  async function mutate(path: string, payload: unknown, method: "post" | "put" | "delete" = "post") {
    if (!data.value) return;
    data.value = await api.write<StateOut>(path, payload, data.value.revision, method);
  }
  async function privateMutate(path: string, payload: unknown = {}, method: "post" | "put" | "delete" = "post") {
    if (!personal.value) return;
    personal.value = await api.write<PersonalOut>(`/me${path}`, payload, personal.value.revision, method);
  }
  return { api, data, personal, members, busy, error, run, refresh, mutate, privateMutate };
}
export type { PlannerSummary };
