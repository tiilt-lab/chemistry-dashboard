import { useEffect, useRef } from "react"
import { TiiltLogo } from "./tiilt-logo"

// TIILT logo accent colors (tiilt.northwestern.edu)
const WAVE_POPS = ["#fbb040", "#00a79d", "#ec008c", "#8dc63f"]

function Waveform() {
    const ref = useRef(null)

    useEffect(() => {
        const canvas = ref.current
        const draw = () => {
            const dpr = window.devicePixelRatio || 1
            const w = canvas.clientWidth
            const h = canvas.clientHeight
            if (!w || !h) return
            canvas.width = w * dpr
            canvas.height = h * dpr
            const ctx = canvas.getContext("2d")
            ctx.scale(dpr, dpr)
            ctx.clearRect(0, 0, w, h)
            const bars = Math.floor(w / 7)
            for (let i = 0; i < bars; i++) {
                // deterministic pseudo-random heights so the render is stable
                const t = Math.sin(i * 12.9898) * 43758.5453
                const r = t - Math.floor(t)
                const amp =
                    0.18 +
                    0.82 * Math.pow(Math.sin((i / bars) * Math.PI), 1.2) * r
                const bh = Math.max(3, amp * h)
                ctx.fillStyle =
                    i % 9 === 4
                        ? WAVE_POPS[((i / 9) | 0) % 4]
                        : "rgba(167,148,201,0.4)"
                ctx.fillRect(i * 7, (h - bh) / 2, 4, bh)
            }
        }
        draw()
        window.addEventListener("resize", draw)
        return () => window.removeEventListener("resize", draw)
    }, [])

    return (
        <canvas
            ref={ref}
            className="mt-auto h-11 w-full opacity-90 md:h-[88px]"
            aria-hidden="true"
        />
    )
}

// The purple identity panel shared by the public pages (login, signup, landing).
function BrandPanel({ pitch = true }) {
    return (
        <aside className="flex flex-col gap-2 bg-tiilt p-5 text-tiilt-panel-text md:gap-4 md:p-10">
            <div className="flex items-center gap-4">
                <TiiltLogo className="h-13 w-13 flex-none md:h-[74px] md:w-[74px]" />
                <div>
                    <div className="text-2xl leading-tight font-extrabold md:text-3xl">
                        BLINC{" "}
                        <span className="font-ahamono text-base font-normal text-tiilt-lavender">
                            (by&nbsp;
                            <a
                                href="https://tiilt.northwestern.edu"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-tiilt-orange hover:underline"
                            >
                                tiilt
                            </a>
                            )
                        </span>
                    </div>
                    <div className="mt-1 font-ahamono text-[11px] tracking-wide uppercase">
                        Building Literacy in N&#8209;person Collaborations
                    </div>
                    <div className="hidden font-ahamono text-[10.5px] tracking-wider text-tiilt-lavender uppercase md:block">
                        TIILT Lab · Northwestern University
                    </div>
                </div>
            </div>
            {pitch && (
                <p className="hidden max-w-[34ch] text-[15px] md:block">
                    Real-time multimodal analytics for group session —
                    speech, attention, and emotion, live from the room.
                </p>
            )}
            <Waveform />
        </aside>
    )
}

// Full-page ground + centered card wrapper shared by the public pages.
function BrandCard({ children }) {
    return (
        <div className="main-container items-center justify-center overflow-y-auto bg-tiilt-ground px-4 py-6">
            <div className="grid w-full max-w-4xl overflow-hidden rounded-xl border border-tiilt-line bg-white shadow-[0_18px_40px_-18px_rgba(42,23,74,0.28)] md:min-h-[480px] md:grid-cols-[5fr_6fr]">
                <BrandPanel />
                <section className="flex flex-col justify-center p-6 md:p-10">
                    {children}
                </section>
            </div>
        </div>
    )
}

export { BrandPanel, BrandCard, Waveform }
