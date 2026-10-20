import { BaseAPI } from "../base/base-clients";
import type { StateOut, PersonalOut } from "../types/household-planner";

export interface PlannerSummary {
  days: { day: string; user_id: string; entries: number; known_entries: number; nutrients: Record<string, number | null> }[];
  cooking: { recipe_id: string; name: string; servings: number }[];
  shopping: { id: string; name: string; state: string; grams: number; recipe_ids: string[] }[];
  notice: string;
}
export class HouseholdPlannerAPI extends BaseAPI {
  base = "/api/households/planning";
  async read<T>(path = ""): Promise<T> {
    const response = await this.requests.get<T>(this.base + path);
    if (response.error || !response.data) throw response.error || new Error("Empty response");
    return response.data;
  }

  async write<T>(path: string, data: unknown, revision: number, method: "post" | "put" | "delete" = "post"): Promise<T> {
    const url = `${this.base}${path}?revision=${revision}`;
    const response = method === "delete" ? await this.requests.delete<T>(url) : method === "post" ? await this.requests.post<T>(url, data) : await this.requests.put<T, unknown>(url, data);
    if (response.error || !response.data) throw response.error || new Error("Empty response");
    return response.data;
  }

  /** Adds the week's summed planner grams to a native list. Not idempotent. */
  async addToShoppingList(planId: string, listId: string): Promise<void> {
    const response = await this.requests.post(`${this.base}/plans/${planId}/shopping-list/${listId}`, {});
    if (response.error) throw response.error;
  }

  state() { return this.read<StateOut>(); }
  personal() { return this.read<PersonalOut>("/me"); }
}
