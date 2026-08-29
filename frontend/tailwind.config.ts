import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1a1a1a",
        paper: "#ffffff",
        accent: "#2d5bff",
      },
    },
  },
  plugins: [],
};

export default config;
