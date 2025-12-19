import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'var(--color-border)',
        ring: 'var(--color-ring, #4c809a)',
        background: 'var(--color-bg-primary)',
        foreground: 'var(--color-text-primary)',
        primary: {
          DEFAULT: 'var(--color-accent-primary)',
          foreground: 'var(--color-primary-foreground, #ffffff)',
        },
        secondary: {
          DEFAULT: 'var(--color-bg-secondary)',
          foreground: 'var(--color-text-primary)',
        },
        destructive: {
          DEFAULT: 'var(--color-error)',
          foreground: '#ffffff',
        },
        muted: {
          DEFAULT: 'var(--color-bg-secondary)',
          foreground: 'var(--color-text-muted)',
        },
        accent: {
          DEFAULT: 'var(--color-bg-secondary)',
          foreground: 'var(--color-text-primary)',
        },
        card: {
          DEFAULT: 'var(--color-bg-primary)',
          foreground: 'var(--color-text-primary)',
        },
        popover: {
          DEFAULT: 'var(--color-bg-primary)',
          foreground: 'var(--color-text-primary)',
        },
      },
      fontFamily: {
        sans: ['var(--db-font-primary)', 'DM Sans', 'sans-serif'],
        heading: ['var(--db-font-accent)', 'Montserrat', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        lg: 'var(--border-radius-lg, 16px)',
        md: 'var(--border-radius-md, 12px)',
        sm: 'var(--border-radius-sm, 4px)',
      },
      spacing: {
        sidebar: 'var(--sidebar-width, 280px)',
        header: 'var(--header-height, 64px)',
      },
    },
  },
  plugins: [],
};

export default config;
