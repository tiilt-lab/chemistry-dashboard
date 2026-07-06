import { useEffect, useRef } from "react"
import QRCode from "qrcode"

// Small canvas QR (used by the session share panel so students can scan
// the join link off a projector).
function QrCode({ value, size = 176 }) {
    const ref = useRef(null)
    useEffect(() => {
        if (ref.current && value) {
            QRCode.toCanvas(ref.current, value, {
                width: size,
                margin: 1,
                color: { dark: "#221a33", light: "#ffffff" },
            })
        }
    }, [value, size])
    if (!value) return null
    return (
        <canvas
            ref={ref}
            role="img"
            aria-label={"QR code for " + value}
            className="mx-auto rounded-lg border border-tiilt-line bg-white p-1"
        />
    )
}

export { QrCode }
