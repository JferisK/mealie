/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AllocationIn {
  id?: string;
  user_id: string;
  recipe_id: string;
  day: string;
  meal: "breakfast" | "lunch" | "dinner" | "snack";
  servings: number;
  batch_id?: string | null;
  note?: string;
}
export interface BatchIn {
  id?: string;
  recipe_id: string;
  servings: number;
  frozen_on: string;
  location?: string;
  note?: string;
}
export interface BatchOut {
  id?: string;
  recipe_id: string;
  servings: number;
  frozen_on: string;
  location?: string;
  note?: string;
  remaining: number;
  facts: RecipeFactsOut;
}
export interface RecipeFactsOut {
  recipe_id: string;
  servings: number;
  cooked_weight_g?: number | null;
  ingredients?: IngredientIn[];
  gluten_free?: "yes" | "no" | "unknown";
  lactose_free?: "yes" | "no" | "unknown";
  freezer_friendly?: "yes" | "no" | "unknown";
  evidence?: string;
  storage_instructions?: string;
  reheating_instructions?: string;
  name: string;
  slug: string;
  image?: string | null;
  per_serving: Nutrients;
  coverage: number;
  updated_at: string;
}
export interface IngredientIn {
  name: string;
  grams: number;
  state?: "raw" | "cooked" | "as_sold";
  per_100g?: Nutrients;
  source?: string;
}
export interface Nutrients {
  calories?: number | null;
  protein?: number | null;
  carbohydrate?: number | null;
  fat?: number | null;
  fiber?: number | null;
}
export interface Contract {}
export interface GoalRevision {
  id?: string;
  created_at: string;
  goals: GoalsIn;
  explanation: string;
  inputs?: {
    [k: string]: number | string;
  };
  confirmed_at?: string | null;
}
export interface GoalsIn {
  calories: number;
  protein: number;
  carbohydrate?: number | null;
  fat?: number | null;
}
export interface HealthSyncIn {
  observations?: ObservationIn[];
  deleted_ids?: string[];
}
export interface ObservationIn {
  id: string;
  kind: "weight_kg" | "height_cm" | "body_fat_percent" | "steps" | "active_kcal" | "resting_kcal" | "workout_minutes";
  value: number;
  at: string;
  source: string;
}
export interface MovementIn {
  id?: string;
  batch_id: string;
  kind: "withdraw" | "discard" | "correction";
  servings: number;
  note?: string;
}
export interface MovementOut {
  id?: string;
  batch_id: string;
  kind: "withdraw" | "discard" | "correction";
  servings: number;
  note?: string;
  at: string;
  actor: string;
}
export interface PersonalOut {
  revision: number;
  state: PersonalState;
  review_due: boolean;
}
export interface PersonalState {
  profile?: ProfileIn;
  observations?: {
    [k: string]: ObservationIn;
  };
  revisions?: GoalRevision[];
  active?: GoalRevision | null;
}
export interface ProfileIn {
  birth_date?: string | null;
  height_cm?: number | null;
  equation_sex?: ("male" | "female") | null;
  activity_factor?: number;
  deficit_kcal?: number;
  protein_reference_kg?: number | null;
  protein_g_per_kg?: number;
  gluten_free?: boolean;
  lactose_free?: boolean;
  avoid_traces?: boolean;
  dislikes?: string[];
}
export interface PlanIn {
  id?: string;
  start: string;
  entries?: AllocationIn[];
}
export interface PlanOut {
  id?: string;
  start: string;
  entries?: AllocationIn[];
  confirmed_at: string;
  native_ids?: number[];
  consumed?: string[];
  checked_items?: string[];
  recipe_snapshots?: {
    [k: string]: RecipeFactsOut;
  };
  shopping_list_id?: string | null;
  shopping_servings?: {
    [k: string]: number;
  };
}
export interface PlannerState {
  facts?: {
    [k: string]: RecipeFactsOut;
  };
  batches?: {
    [k: string]: BatchOut;
  };
  movements?: {
    [k: string]: MovementOut;
  };
  plans?: {
    [k: string]: PlanOut;
  };
  ideas?: {
    [k: string]: IdeaOut;
  };
}
export interface IdeaIn {
  id?: string;
  week_start: string;
  recipe_id: string;
  note?: string;
}
export interface IdeaOut {
  id?: string;
  week_start: string;
  recipe_id: string;
  note?: string;
  name: string;
  slug: string;
  proposed_by: string;
  created_at: string;
  likes?: string[];
}
export interface RecipeFactsIn {
  recipe_id: string;
  servings: number;
  cooked_weight_g?: number | null;
  ingredients?: IngredientIn[];
  gluten_free?: "yes" | "no" | "unknown";
  lactose_free?: "yes" | "no" | "unknown";
  freezer_friendly?: "yes" | "no" | "unknown";
  evidence?: string;
  storage_instructions?: string;
  reheating_instructions?: string;
}
export interface StateOut {
  revision: number;
  state: PlannerState;
}
