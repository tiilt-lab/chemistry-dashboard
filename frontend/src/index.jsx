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

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<><React.StrictMode>
     <PageRouter/>
  </React.StrictMode></>);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
