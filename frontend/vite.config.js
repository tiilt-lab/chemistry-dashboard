import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import eslint from "vite-plugin-eslint";
import tailwindcss from "@tailwindcss/vite";
//import svgr from "vite-plugin-svgr";

export default defineConfig(() => {
  return {
    resolve: {
      alias: {
        "~": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      outDir: "build",
    },
    plugins: [
      react(),
      eslint(),
      tailwindcss(),
  //    svgr({ svgrOptions: { icon: true }, include: "**/*.svg?react" }),
    ],
  };
});
