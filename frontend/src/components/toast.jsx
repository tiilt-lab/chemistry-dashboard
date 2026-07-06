// Bottom-right notification stack (analysis completions).
function ToastStack({ toasts, dismiss }) {
    if (!toasts || !toasts.length) return null
    return (
        <div
            role="status"
            aria-live="polite"
            className="fixed right-4 bottom-4 z-50 flex w-72 flex-col gap-2"
        >
            {toasts.map((t) => (
                <div
                    key={t.id}
                    className="flex items-center gap-2 rounded-xl border border-tiilt-line bg-white px-3.5 py-2.5 text-sm text-tiilt-ink shadow-pop"
                >
                    <span className="h-2 w-2 flex-none rounded-full bg-tiilt-teal" />
                    <span className="min-w-0 grow">{t.text}</span>
                    <button
                        onClick={() => dismiss(t.id)}
                        aria-label="Dismiss notification"
                        className="flex-none cursor-pointer rounded p-0.5 text-tiilt-muted transition hover:text-tiilt-ink"
                    >
                        ✕
                    </button>
                </div>
            ))}
        </div>
    )
}

export { ToastStack }
