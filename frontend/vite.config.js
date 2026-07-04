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
        server: {
            port: 3000,
            proxy: {
                "/api": {
                    target: "http://localhost:5001",
                    changeOrigin: false,
                },
                "/socket.io": {
                    target: "http://localhost:5001",
                    changeOrigin: false,
                    ws: true,
                },
            },
        },
        build: {
            outDir: "build",
            sourcemap: true,
        },
    }
})
