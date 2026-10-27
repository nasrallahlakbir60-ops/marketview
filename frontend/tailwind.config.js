/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--c-${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: token("surface"),
        panel: token("panel"),
        "panel-hover": token("panel-hover"),
        fg: token("fg"),
        muted: token("muted"),
        subtle: token("subtle"),
        faint: token("faint"),
        line: token("line"),
        accent: token("accent"),
        "on-accent": token("on-accent"),
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      keyframes: {
        "news-in": {
          "0%": { opacity: "0", transform: "translateY(-6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "news-in": "news-in 0.45s ease-out",
      },
    },
  },
  plugins: [],
};
