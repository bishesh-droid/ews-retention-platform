/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#f0f4ff',
                    100: '#e1e9ff',
                    200: '#c3d3ff',
                    300: '#a5bdff',
                    400: '#87a7ff',
                    500: '#6991ff',
                    600: '#5474cc',
                    700: '#3f5799',
                    800: '#2a3a66',
                    900: '#151d33',
                },
                slate: {
                    850: '#1e293b',
                    950: '#0f172a',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                display: ['Outfit', 'sans-serif'],
            },
            boxShadow: {
                'soft': '0 4px 20px 0 rgba(0, 0, 0, 0.05)',
                'glow': '0 0 15px rgba(105, 145, 255, 0.3)',
            },
        },
    },
    plugins: [],
}
