import { useNavigate, Link } from "react-router-dom"
import { useEffect, useState } from "react"
import { AuthService } from "../services/auth-service"
import { BrandCard } from "../components/brand-panel"

function LoginPage() {
    const navigate = useNavigate()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [showPassword, setShowPassword] = useState(false)
    const [errors, setErrors] = useState({})
    const [loading, setLoading] = useState(false)
    const [loginStatus, setLoginStatus] = useState(0)
    const [authObject, setAuthObject] = useState(null)

    useEffect(() => {
        if (loginStatus.status === 200 && authObject !== null) {
            return navigate("/home")
        } else if (loginStatus.status === 400) {
            setLoading(false)
            setErrors({
                form: loginStatus.message || "Login failed. Please try again.",
            })
        } else if (loginStatus.status === 401) {
            return navigate("/login")
        } else if (loginStatus.status === 600) {
            setLoading(false)
            setErrors({ form: "Invalid email or password." })
        }
    }, [loginStatus, authObject])

    const handleSubmit = (event) => {
        event.preventDefault()
        const next = {}
        if (!email.trim()) next.email = "Enter your email address."
        if (!password.trim()) next.password = "Enter your password."
        setErrors(next)
        if (next.email || next.password) return
        setLoading(true)
        new AuthService().login(
            email.trim(),
            password.trim(),
            setLoginStatus,
            setAuthObject,
        )
    }

    const inputClass = (invalid) =>
        `h-12 w-full rounded-lg border bg-white px-3.5 text-base text-tiilt-ink outline-none transition ` +
        `focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30 ` +
        (invalid ? "border-tiilt-danger" : "border-tiilt-line")

    return (
        <BrandCard>
            <Link
                to="/"
                className="mb-4 text-sm font-semibold text-tiilt-muted hover:text-tiilt"
            >
                &larr; Back
            </Link>
            <h2 className="text-xl font-semibold text-tiilt-ink">Sign in</h2>
            <p className="mt-1 mb-6 text-sm text-tiilt-muted">
                Use your instructor or researcher account.
            </p>

            <form
                className="flex max-w-md flex-col gap-4"
                onSubmit={handleSubmit}
                noValidate
            >
                <div className="flex flex-col gap-1.5">
                    <label
                        htmlFor="email"
                        className="text-sm font-semibold text-tiilt-ink"
                    >
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
                    {errors.email && (
                        <div
                            role="alert"
                            className="rounded-md bg-tiilt-danger-soft px-3 py-1.5 text-[13px] text-tiilt-danger"
                        >
                            {errors.email}
                        </div>
                    )}
                </div>

                <div className="flex flex-col gap-1.5">
                    <label
                        htmlFor="password"
                        className="text-sm font-semibold text-tiilt-ink"
                    >
                        Password
                    </label>
                    <div className="relative flex">
                        <input
                            id="password"
                            name="password"
                            type={showPassword ? "text" : "password"}
                            autoComplete="current-password"
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
                    {errors.password && (
                        <div
                            role="alert"
                            className="rounded-md bg-tiilt-danger-soft px-3 py-1.5 text-[13px] text-tiilt-danger"
                        >
                            {errors.password}
                        </div>
                    )}
                </div>

                {errors.form && (
                    <div
                        role="alert"
                        className="rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger"
                    >
                        {errors.form}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading}
                    className="flex h-12 items-center justify-center gap-2.5 rounded-lg bg-tiilt text-base font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px disabled:opacity-70"
                >
                    {loading ? (
                        <>
                            <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                            Signing in…
                        </>
                    ) : (
                        "Sign in"
                    )}
                </button>

                <div className="text-sm text-tiilt-muted">
                    New here?{" "}
                    <Link
                        to="/signup"
                        className="font-semibold text-tiilt hover:underline"
                    >
                        Create an account
                    </Link>
                </div>
            </form>
        </BrandCard>
    )
}

export { LoginPage }
