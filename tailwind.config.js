/** @type {import('tailwindcss').Config} */
export default {
  // Вказуємо шляхи до всіх файлів, де використовуються класи Tailwind
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}", 
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}