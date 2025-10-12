/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'voice-primary': '#667eea',
        'voice-secondary': '#764ba2',
        'voice-accent': '#10b981',
        'voice-muted': '#6b7280',
        'voice-text': '#374151',
        'voice-crisis': '#dc2626',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'breathing': 'breathing 2s ease-in-out infinite',
        'listening': 'listening 1s ease-in-out infinite',
      },
      keyframes: {
        breathing: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.8' },
          '50%': { transform: 'scale(1.05)', opacity: '1' },
        },
        listening: {
          '0%, 100%': { 
            transform: 'scale(1)',
            boxShadow: '0 0 0 0 rgba(102, 126, 234, 0.7)'
          },
          '50%': { 
            transform: 'scale(1.1)',
            boxShadow: '0 0 0 10px rgba(102, 126, 234, 0)'
          },
        },
      },
    },
  },
  plugins: [],
}
