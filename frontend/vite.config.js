import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import eslint from "vite-plugin-eslint"
import tailwindcss from "@tailwindcss/vite"


// The API the dev server proxies to. 5001 is where gunicorn listens on the
// production host, so a dev frontend there talks to the live API; a server
// started by hand on another port is reached with
//     DC_API_TARGET=http://localhost:5091 npm start
const apiTarget = process.env.DC_API_TARGET || "http://localhost:5001"

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
                    target: apiTarget,
                    changeOrigin: false,
                },
                "/socket.io": {
                    target: apiTarget,
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
