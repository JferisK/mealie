import type { InjectionKey, Ref } from "vue";

// Lets planner sections put their reload action into the shared page header
// instead of each section drawing its own refresh button somewhere else.
interface PlannerPageContext {
  refresh: Ref<(() => void) | null>;
  busy: Ref<boolean>;
}

const KEY: InjectionKey<PlannerPageContext> = Symbol("planner-page");

export function providePlannerPage(): PlannerPageContext {
  const context = { refresh: ref<(() => void) | null>(null), busy: ref(false) };
  provide(KEY, context);
  return context;
}

export function usePlannerPageRefresh(refresh: () => void, busy: Ref<boolean>) {
  const context = inject(KEY, null);
  if (!context) return;
  context.refresh.value = refresh;
  watch(busy, value => (context.busy.value = value), { immediate: true });
  onBeforeUnmount(() => (context.refresh.value = null));
}
