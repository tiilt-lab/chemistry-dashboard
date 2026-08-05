import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import eslint from "vite-plugin-eslint"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig(() => {
    return {
        plugins: [react(), eslint(), tailwindcss()],
        server: {
            proxy: {
                '/api': 'http://localhost:5000',
                '/socket.io': {
                    target: 'http://localhost:5000',
                    ws: true,
                },
                '/audio_socket': {
                    target: 'http://localhost:9002',
                    ws: true,
                }
            },
            historyApiFallback: true
        },
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
            rollupOptions: {
                output: {
                    manualChunks(id) {
                        if (id.indexOf("node_modules") !== -1) {
                            const basic = id
                                .toString()
                                .split("node_modules/")[1]
                            const sub1 = basic.split("/")[0]
                            if (sub1 !== ".pnpm") {
                                return sub1.toString()
                            }
                            const name2 = basic.split("/")[1]
                            return name2
                                .split("@")
                                [name2[0] === "@" ? 1 : 0].toString()
                        }
                    },
                },
            },
            sourcemap: true,
        },
    }
})