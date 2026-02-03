import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

const adminKey = import.meta.env.VITE_ADMIN_API_KEY
if (adminKey) {
    const originalFetch = window.fetch.bind(window)
    window.fetch = (input, init = {}) => {
        const headers = new Headers(init.headers || {})
        headers.set('X-Admin-Key', adminKey)
        return originalFetch(input, { ...init, headers })
    }
}

ReactDOM.createRoot(document.getElementById('app')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
