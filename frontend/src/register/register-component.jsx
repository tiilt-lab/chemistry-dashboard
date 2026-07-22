import { useNavigate, Link } from "react-router-dom"
import { useState } from "react"
import { InlineSpinner } from "../components/inline-spinner"
import { btnPrimaryTall } from "../components/dialog-styles"
import { AuthService } from "../services/auth-service"
import { BrandCard } from "../components/brand-panel"

// Instructor / researcher sign-up. This creates a login account (role 'user'),
// which a super can promote to admin afterwards. It is not /signup — that page
// enrols a study participant's voice and face and creates no login at all.
function RegisterPage() {
    const navigate = useNavigate()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [confirm, setConfirm] = useState("")
    const [showPassword, setShowPassword] = useState(false)
    const [errors, setErrors] = useState({})
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (event) => {
        event.preventDefault()
        const next = {}
        if (!email.trim()) next.email = "Enter your email address."
        if (!password) next.password = "Choose a password."
        if (!confirm) next.confirm = "Re-enter your password."
        else if (password !== confirm) next.confirm = "The two passwords do not match."
        setErrors(next)
        if (next.email || next.password || next.confirm) return

        setLoading(true)
        const result = await new AuthService().register(email.trim(), password, confirm)
        if (result.ok) {
            // The server signs the new account in, so go straight to the app.
            return navigate("/home")
        }
        setLoading(false)
        setErrors({ form: result.message })
    }

    const inputClass = (invalid) =>
        `h-12 w-full rounded-lg border bg-white px-3.5 text-base text-tiilt-ink outline-none transition ` +
        `focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30 ` +
        (invalid ? "border-tiilt-danger" : "border-tiilt-line")

    const fieldError = (message) =>
        message ? (
            <div
                role="alert"
                className="rounded-md bg-tiilt-danger-soft px-3 py-1.5 text-[13px] text-tiilt-danger"
            >
                {message}
            </div>
        ) : null

    return (
        <BrandCard>
            <Link
                to="/login"
                className="mb-4 text-sm font-semibold text-tiilt-muted hover:text-tiilt"
            >
                &larr; Back
            </Link>
            <h1 className="text-xl font-semibold text-tiilt-ink">Create an account</h1>
            <p className="mt-1 mb-6 text-sm text-tiilt-muted">
                For instructors and researchers who run sessions. Study
                participants do not need one — they join with a passcode.
            </p>

            <form
                className="flex max-w-md flex-col gap-4"
                onSubmit={handleSubmit}
                noValidate
            >
                <div className="flex flex-col gap-1.5">
                    <label htmlFor="email" className="text-sm font-semibold text-tiilt-ink">
                        Email
                    </label>
                    <input
                        id="email"
                        name="username"
                        type="email"
                        autoComplete="username"
                        autoCapitalize="off"
                        spellCheck="false"
                        placeholder="you@u.northwestern.edu"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className={inputClass(errors.email)}
                    />
                    {fieldError(errors.email)}
                </div>

                <div className="flex flex-col gap-1.5">
                    <label htmlFor="password" className="text-sm font-semibold text-tiilt-ink">
                        Password
                    </label>
                    <div className="relative flex">
                        <input
                            id="password"
                            name="password"
                            type={showPassword ? "text" : "password"}
                            autoComplete="new-password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className={inputClass(errors.password)}
                        />
                        <button
                            type="button"
                            aria-pressed={showPassword}
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded-md px-2.5 py-2 text-xs font-semibold text-tiilt-muted hover:text-tiilt"
                        >
                            {showPassword ? "Hide" : "Show"}
                        </button>
                    </div>
                    {/* Mirrors User.validate_password on the server, so the
                        rules are visible before the request rather than as a
                        rejection afterwards. */}
                    <div className="text-[13px] text-tiilt-muted">
                        At least 8 characters, with an uppercase letter, a
                        lowercase letter, a digit, and a special character.
                    </div>
                    {fieldError(errors.password)}
                </div>

                <div className="flex flex-col gap-1.5">
                    <label htmlFor="confirm" className="text-sm font-semibold text-tiilt-ink">
                        Confirm password
                    </label>
                    <input
                        id="confirm"
                        name="confirm"
                        type={showPassword ? "text" : "password"}
                        autoComplete="new-password"
                        placeholder="••••••••"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        className={inputClass(errors.confirm)}
                    />
                    {fieldError(errors.confirm)}
                </div>

                {errors.form && (
                    <div
                        role="alert"
                        className="rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger"
                    >
                        {errors.form}
                    </div>
                )}

                <button type="submit" className={btnPrimaryTall} disabled={loading}>
                    {loading ? <InlineSpinner /> : "Create account"}
                </button>

                <div className="text-sm text-tiilt-muted">
                    Already have an account?{" "}
                    <Link to="/login" className="font-semibold text-tiilt hover:underline">
                        Sign in
                    </Link>
                </div>
                <div className="text-sm text-tiilt-muted">
                    Here as a study participant?{" "}
                    <Link to="/signup" className="font-semibold text-tiilt hover:underline">
                        Enroll your voice and face
                    </Link>
                </div>
            </form>
        </BrandCard>
    )
}

export { RegisterPage }
