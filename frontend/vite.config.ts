import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Privacidade: dev server sempre em localhost, nunca exposto publicamente.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
  },
});
