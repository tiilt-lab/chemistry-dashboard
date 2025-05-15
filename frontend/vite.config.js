import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import eslint from "vite-plugin-eslint"
import tailwindcss from "@tailwindcss/vite"


export default defineConfig(() => {
    return {
        plugins: [
            react(), 
            eslint(), 
            tailwindcss()
        ],
        resolve: {
            alias: {
                "@": path.resolve(__dirname, "./src"),
                "@assets": path.resolve(__dirname, "./src/assets"),
                "@components": path.resolve(__dirname, "./src/components"),
                "@icons": path.resolve(__dirname, "./src/Icons"),
            },
        },
        build: {
            outDir: "build",
            sourcemap: true,
        },
    }
})
