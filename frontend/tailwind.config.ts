import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#173f3c",
        paper: "#fffdf6",
        sand: "#f4f0e6",
        muted: "#687b74",
        teal: "#28584f",
        pink: "#cf4f79",
        rule: "#d8cfc0",
        brass: "#b8860b",
        flag: "#c23b22",
        ok: "#2f6b4f",
        always: "#8b1e3f",
        deckonly: "#1f4e5f",
      },
      fontFamily: {
        display: ['"Segoe Print"', '"Comic Sans MS"', "cursive"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        pin: "0 2px 0 rgba(27,25,20,0.25)",
      },
    },
  },
  plugins: [],
};

export default config;
