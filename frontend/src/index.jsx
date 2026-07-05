import React from 'react';
import ReactDOM from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import { PageRouter } from './routes/routes-pages';
import './index.css'
// Dark mode: apply persisted choice (or system preference) before first paint.
const _savedTheme = localStorage.getItem("theme")
if (_savedTheme === "dark" || (!_savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    document.documentElement.classList.add("dark")
}
function ThemeToggle() {
    const [dark, setDark] = React.useState(
        document.documentElement.classList.contains("dark"),
    )
    const flip = () => {
        const next = !dark
        document.documentElement.classList.toggle("dark", next)
        localStorage.setItem("theme", next ? "dark" : "light")
        setDark(next)
    }
    return (
        <button
            onClick={flip}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
            style={{ position: "fixed", right: "14px", bottom: "14px", zIndex: 60 }}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-tiilt-line bg-white text-base shadow-md transition hover:border-tiilt"
        >
            {dark ? "\u2600\ufe0f" : "\ud83c\udf19"}
        </button>
    )
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<><React.StrictMode>
     <PageRouter/>
  </React.StrictMode><ThemeToggle /></>);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
