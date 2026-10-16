// Fork: Vuetify's number inputs parse with the UI locale. In German "87.6" is
// read as a grouping dot and becomes 876 (then clamped to the max), so a typed
// "." is turned into the locale's decimal separator before Vuetify sees it.
export default defineNuxtPlugin(() => {
  document.addEventListener("beforeinput", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement) || event.data !== ".") return;
    if (!target.closest(".v-number-input")) return;
    const decimal = (1.5).toLocaleString(document.documentElement.lang || navigator.language).charAt(1);
    if (decimal === "." || target.value.includes(decimal)) return;
    event.preventDefault();
    const start = target.selectionStart ?? target.value.length;
    const end = target.selectionEnd ?? start;
    target.setRangeText(decimal, start, end, "end");
    target.dispatchEvent(new Event("input", { bubbles: true }));
  }, true);
});
