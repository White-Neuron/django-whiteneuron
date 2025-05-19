module.exports = {
  content: ["./**/*.{html,py,js}"],
  media: false,
  darkMode: "class",
  plugins: [
    require('daisyui'),
  ],
  daisyui: {
      themes: ['light', 'dark'],
      prefix: 'ui-',
  },
  theme: {
    extend: {
      colors: {
        primary: {
          50: "rgb(var(--color-sky-100) / <alpha-value>)",
          100: "rgb(var(--color-sky-100) / <alpha-value>)",
          200: "rgb(var(--color-sky-200) / <alpha-value>)",
          300: "rgb(var(--color-sky-300) / <alpha-value>)",
          400: "rgb(var(--color-sky-400) / <alpha-value>)",
          500: "rgb(var(--color-sky-500) / <alpha-value>)",
          600: "rgb(var(--color-sky-600) / <alpha-value>)",
          700: "rgb(var(--color-sky-700) / <alpha-value>)",
          800: "rgb(var(--color-sky-800) / <alpha-value>)",
          900: "rgb(var(--color-sky-900) / <alpha-value>)",
        },
      },
      fontSize: {
        0: [0, 1],
        xxs: ["11px", "14px"],
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      minWidth: {
        sidebar: "18rem",
      },
      spacing: {
        68: "17rem",
        128: "32rem",
      },
      transitionProperty: {
        height: "height",
        width: "width",
      },
      width: {
        sidebar: "18rem",
      },
    },
  },
  variants: {
    extend: {
      borderColor: ["checked", "focus-within", "hover"],
      display: ["group-hover"],
      overflow: ["hover"],
      textColor: ["hover"],
    },
  },
};
