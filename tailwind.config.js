/** Tailwind build config - mirrors the inline `tailwind.config` previously
 *  injected by the Play CDN in places/base.html. */
module.exports = {
  darkMode: 'class',
  content: [
    './templates/**/*.html',
    './places/templates/**/*.html',
    './blog/templates/**/*.html',
    './contact/templates/**/*.html',
    './feedback/templates/**/*.html',
    './prayer_times/templates/**/*.html',
    './reviews/templates/**/*.html',
    './users/templates/**/*.html',
    './utils/templates/**/*.html',
    './static/js/**/*.js',
    './**/*.py',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Ubuntu', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        teal: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
        },
        dark: {
          bg: '#111827',
          card: '#1f2937',
          border: '#374151',
          text: '#f9fafb',
          muted: '#9ca3af',
        },
        backdropBlur: {
          'xs': '2px',
        },
        backgroundImage: {
          'gradient-primary': 'linear-gradient(to right, var(--tw-gradient-stops))',
          'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        },
      },
    },
  },
  plugins: [],
}
