export interface ThemeConfig {
  lightPrimary: string;
  lightAccent: string;
  lightSecondary: string;
  lightSuccess: string;
  lightInfo: string;
  lightWarning: string;
  lightError: string;
  darkPrimary: string;
  darkAccent: string;
  darkSecondary: string;
  darkSuccess: string;
  darkInfo: string;
  darkWarning: string;
  darkError: string;
}

let __cachedTheme: ThemeConfig | undefined;

async function fetchTheme(): Promise<ThemeConfig | undefined> {
  const route = "/api/app/about/theme";

  try {
    const response = await fetch(route);
    const data = await response.json();
    return data as ThemeConfig;
  }
  catch {
    return undefined;
  }
}

export default defineNuxtPlugin(async (nuxtApp) => {
  nuxtApp.hook("vuetify:before-create", async ({ vuetifyOptions }) => {
    let theme = __cachedTheme;
    if (!theme) {
      theme = await fetchTheme();
      __cachedTheme = theme;
    }
    // Fork reskin: flatter, rounder components; colours come from the theme below.
    vuetifyOptions.defaults = {
      ...vuetifyOptions.defaults,
      VCard: { rounded: "lg" },
      VBtn: { rounded: "lg" },
      VChip: { rounded: "pill" },
      VAlert: { rounded: "lg" },
      VDialog: { VCard: { rounded: "xl" } },
    };
    vuetifyOptions.theme = {
      defaultTheme: nuxtApp.$config.public.useDark ? "dark" : "light",
      variations: {
        colors: ["primary", "accent", "secondary", "success", "info", "warning", "error", "background"],
        lighten: 3,
        darken: 3,
      },
      themes: {
        light: {
          dark: false,
          colors: {
            primary: theme?.lightPrimary ?? "#2F6B4F",
            accent: theme?.lightAccent ?? "#4A6072",
            secondary: theme?.lightSecondary ?? "#C98A1B",
            success: theme?.lightSuccess ?? "#2F6B4F",
            info: theme?.lightInfo ?? "#4A6072",
            warning: theme?.lightWarning ?? "#D9822B",
            error: theme?.lightError ?? "#C2413A",
            background: "#F4F6F5",
            surface: "#FFFFFF",
          },
        },
        dark: {
          dark: true,
          colors: {
            primary: theme?.darkPrimary ?? "#7FBF9E",
            accent: theme?.darkAccent ?? "#AFC2D0",
            secondary: theme?.darkSecondary ?? "#E8B44F",
            success: theme?.darkSuccess ?? "#7FBF9E",
            info: theme?.darkInfo ?? "#AFC2D0",
            warning: theme?.darkWarning ?? "#EFA35B",
            error: theme?.darkError ?? "#E5776F",
            background: "#141917",
            surface: "#1B211E",
          },
        },
      },
    };
  });
});
