/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#0B2545",
          light: "#102C54",
          dark: "#16284A",
        },
        cyan: {
          DEFAULT: "#17B6E0",
          light: "#0EC0E8",
          pale: "#E3F7FC",
        },
        surface: "#F4F6F8",
        border: "#E3E7EE",
        muted: "#6B7686",
        panel: "#EDEFF2",
        lavender: "#E8ECF7",
        success: { DEFAULT: "#1BAA5E", bg: "#E7F8EE" },
        warning: { DEFAULT: "#F5A623", bg: "#FEF4E2" },
        danger: { DEFAULT: "#E0524C", bg: "#FDEAEA" },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      borderRadius: {
        lg: "20px",
        xl: "28px",
      },
      boxShadow: {
        card: "0 4px 18px rgba(11,37,69,0.08)",
        pop: "0 14px 34px rgba(11,37,69,0.18)",
      },
    },
  },
  plugins: [],
};
