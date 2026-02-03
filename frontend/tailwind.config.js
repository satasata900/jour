/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    // Safelist for dynamic color classes used in components
    safelist: [
        // Amber (interval/hourly)
        'bg-amber-500', 'bg-amber-500/10', 'bg-amber-500/20',
        'text-amber-400', 'text-amber-500',
        'border-amber-500/30', 'shadow-amber-500/10',
        // Emerald (daily)
        'bg-emerald-500', 'bg-emerald-500/10', 'bg-emerald-500/20',
        'text-emerald-400', 'text-emerald-500',
        'border-emerald-500/30', 'shadow-emerald-500/10',
        // Blue (weekly)
        'bg-blue-500', 'bg-blue-500/10', 'bg-blue-500/20',
        'text-blue-400', 'text-blue-500',
        'border-blue-500/30', 'shadow-blue-500/10',
        // Purple (monthly)
        'bg-purple-500', 'bg-purple-500/10', 'bg-purple-500/20',
        'text-purple-400', 'text-purple-500',
        'border-purple-500/30', 'shadow-purple-500/10',
    ],
    theme: {
        extend: {
            colors: {
                background: "#09090b",
                surface: "#18181b",
                primary: "#3b82f6",
                secondary: "#a1a1aa",
                accent: "#22c55e",
                border: "#27272a",
            },
            fontFamily: {
                sans: ['"IBM Plex Sans Arabic"', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
