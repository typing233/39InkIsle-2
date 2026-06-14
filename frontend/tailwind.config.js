/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        sepia: {
          50: '#fdf8f0',
          100: '#f5ead6',
          200: '#e8d5b0',
          800: '#5c4a2a',
          900: '#3d3019',
        },
      },
    },
  },
  plugins: [],
};
