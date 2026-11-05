import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react"

/**
 * Crolo theme — a minimalist, dark-first design system built on Chakra UI v3.
 *
 * The palette is intentionally narrow: near-black neutrals for surfaces and a
 * single "brand" accent, so the UI stays quiet and content-led.
 */
const config = defineConfig({
  theme: {
    tokens: {
      colors: {
        // Neutral ramp tuned for dark surfaces (Zinc-like, slightly cooler).
        gray: {
          50: { value: "#fafafa" },
          100: { value: "#f4f4f5" },
          200: { value: "#e4e4e7" },
          300: { value: "#d4d4d8" },
          400: { value: "#a1a1aa" },
          500: { value: "#71717a" },
          600: { value: "#52525b" },
          700: { value: "#3f3f46" },
          800: { value: "#27272a" },
          900: { value: "#18181b" },
          950: { value: "#101012" },
        },
        // The single accent color used for primary actions and focus rings.
        brand: {
          50: { value: "#eef4ff" },
          100: { value: "#d9e6ff" },
          200: { value: "#bcd4ff" },
          300: { value: "#8eb8ff" },
          400: { value: "#6997ff" },
          500: { value: "#4b7cf7" },
          600: { value: "#3563e9" },
          700: { value: "#2b4ec7" },
          800: { value: "#27429f" },
          900: { value: "#243a7d" },
          950: { value: "#16244b" },
        },
      },
    },
    semanticTokens: {
      colors: {
        // Surfaces
        bg: {
          DEFAULT: {
            value: { _light: "{colors.white}", _dark: "#0b0b0d" },
          },
          subtle: {
            value: { _light: "{colors.gray.50}", _dark: "#101013" },
          },
          muted: {
            value: { _light: "{colors.gray.100}", _dark: "#151518" },
          },
          emphasized: {
            value: { _light: "{colors.gray.200}", _dark: "#1d1d21" },
          },
          inverted: {
            value: { _light: "{colors.gray.950}", _dark: "{colors.gray.50}" },
          },
          panel: {
            value: { _light: "{colors.white}", _dark: "#101013" },
          },
          error: {
            value: { _light: "{colors.red.50}", _dark: "#1f1113" },
          },
          warning: {
            value: { _light: "{colors.orange.50}", _dark: "#20150c" },
          },
          success: {
            value: { _light: "{colors.green.50}", _dark: "#0c1a12" },
          },
          info: {
            value: { _light: "{colors.blue.50}", _dark: "#0c1524" },
          },
        },
        // Foreground text
        fg: {
          DEFAULT: {
            value: { _light: "{colors.gray.950}", _dark: "#f2f2f3" },
          },
          muted: {
            value: { _light: "{colors.gray.600}", _dark: "{colors.gray.400}" },
          },
          subtle: {
            value: { _light: "{colors.gray.400}", _dark: "{colors.gray.500}" },
          },
          inverted: {
            value: { _light: "{colors.gray.50}", _dark: "#0b0b0d" },
          },
        },
        // Status colors are kept low-contrast so they read as subtle hints
        // rather than alerts. Only the border and text carry the hue.
        border: {
          DEFAULT: {
            value: { _light: "{colors.gray.200}", _dark: "#232327" },
          },
          muted: {
            value: { _light: "{colors.gray.100}", _dark: "#1a1a1e" },
          },
          subtle: {
            value: { _light: "{colors.gray.50}", _dark: "#141417" },
          },
          emphasized: {
            value: { _light: "{colors.gray.300}", _dark: "#34343a" },
          },
          success: {
            value: { _light: "{colors.green.400}", _dark: "rgba(52, 211, 153, 0.35)" },
          },
          error: {
            value: { _light: "{colors.red.400}", _dark: "rgba(248, 113, 113, 0.35)" },
          },
          warning: {
            value: { _light: "{colors.orange.400}", _dark: "rgba(251, 146, 60, 0.35)" },
          },
          info: {
            value: { _light: "{colors.blue.400}", _dark: "rgba(96, 165, 250, 0.35)" },
          },
        },
        // Brand semantic palette (enables `colorPalette="brand"`)
        brand: {
          contrast: { value: { _light: "white", _dark: "white" } },
          fg: {
            value: { _light: "{colors.brand.700}", _dark: "{colors.brand.300}" },
          },
          subtle: {
            value: { _light: "{colors.brand.50}", _dark: "{colors.brand.950}" },
          },
          muted: {
            value: { _light: "{colors.brand.100}", _dark: "{colors.brand.900}" },
          },
          emphasized: {
            value: { _light: "{colors.brand.200}", _dark: "{colors.brand.800}" },
          },
          solid: {
            value: { _light: "{colors.brand.600}", _dark: "{colors.brand.600}" },
          },
          focusRing: {
            value: { _light: "{colors.brand.500}", _dark: "{colors.brand.400}" },
          },
          border: {
            value: { _light: "{colors.brand.500}", _dark: "{colors.brand.400}" },
          },
        },
      },
    },
  },
})

export const system = createSystem(defaultConfig, {
  ...config,
  globalCss: {
    "html, body": {
      bg: "bg",
      color: "fg",
      minHeight: "100dvh",
    },
    "::selection": {
      bg: "brand.solid/30",
    },
    "button, [role=button], [role=menuitem]": {
      cursor: "pointer",
    },
    "button:disabled, [role=button][aria-disabled=true]": {
      cursor: "not-allowed",
    },
    "*": {
      scrollbarColor: "var(--chakra-colors-border-emphasized) transparent",
    },
    "*::-webkit-scrollbar": {
      width: "10px",
      height: "10px",
    },
    "*::-webkit-scrollbar-thumb": {
      bg: "border.emphasized",
      borderRadius: "full",
      borderWidth: "2px",
      borderStyle: "solid",
      borderColor: "transparent",
      backgroundClip: "content-box",
    },
  },
})
