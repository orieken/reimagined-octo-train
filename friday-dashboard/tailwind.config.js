// tailwind.config.js
export default {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  purge: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#63B3ED',
          DEFAULT: '#3182CE',
          dark: '#2B6CB0',
        },
        secondary: {
          light: '#EDF2F7',
          DEFAULT: '#A0AEC0',
          dark: '#4A5568',
        },
        success: {
          light: '#C6F6D5',
          DEFAULT: '#48BB78',
          dark: '#2F855A',
        },
        danger: {
          light: '#FED7D7',
          DEFAULT: '#F56565',
          dark: '#C53030',
        },
        warning: {
          light: '#FEEBC8',
          DEFAULT: '#ED8936',
          dark: '#C05621',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif']
      }
    },
  },
  plugins: [],
}
