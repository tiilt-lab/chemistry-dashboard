// Small border spinner for button/inline loading states (the big lds-ring
// AppSpinner stays for page-level loads).
function InlineSpinner({ className = "" }) {
    return (
        <span
            aria-hidden="true"
            className={
                "inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" +
                (className ? " " + className : "")
            }
        />
    )
}

export { InlineSpinner }
