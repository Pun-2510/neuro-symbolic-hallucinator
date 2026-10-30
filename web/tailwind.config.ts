import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      /* Verdict Colors & Solva Warm Editorial Palette */
      colors: {
        slate: {
          50: '#FBFAF6',
          100: '#F4F2EC',
          200: '#E7E3D9',
          300: '#D6D0C4',
          400: '#8C887E',
          500: '#6E695F',
          600: '#56524A',
          700: '#3D3A33',
          800: '#26231D',
          900: '#1C1A15',
          950: '#141310',
        },
        indigo: {
          50: '#F4F2EC',
          100: '#ECE9E0',
          200: '#E7E3D9',
          300: '#D6D0C4',
          400: '#B8B1A4',
          500: '#56524A',
          600: '#1C1A15',
          700: '#2E2B23',
          800: '#3A352C',
          900: '#24211B',
          950: '#181612',
        },
        verdict: {
          verified: 'hsl(var(--verdict-verified))',
          'metadata-error': 'hsl(var(--verdict-metadata-error))',
          suspected: 'hsl(var(--verdict-suspected))',
          unresolved: 'hsl(var(--verdict-unresolved))',
        },
        mapping: {
          matched: 'hsl(var(--mapping-matched))',
          missing: 'hsl(var(--mapping-missing))',
          uncited: 'hsl(var(--mapping-uncited))',
          mismatch: 'hsl(var(--mapping-mismatch))',
          duplicate: 'hsl(var(--mapping-duplicate))',
          ambiguous: 'hsl(var(--mapping-ambiguous))',
          style: 'hsl(var(--mapping-style))',
          unresolved: 'hsl(var(--mapping-unresolved))',
        },
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--success-foreground))',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
          hover: 'hsl(var(--primary-hover))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
      },

      /* Border Radius */
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        xl: 'calc(var(--radius) + 4px)',
      },

      /* Shadows */
      boxShadow: {
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
      },

      /* Font Family — Unified Solva Editorial System (Onest + Sentient) */
      fontFamily: {
        sans: ['Onest', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['Sentient', 'Source Serif 4', 'Georgia', 'serif'],
        display: ['Sentient', 'Source Serif 4', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },

      /* Animation */
      animation: {
        'fade-in': 'fadeIn 200ms ease-out',
        'slide-up': 'slideUp 300ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slideDown 200ms ease-out',
        'scale-in': 'scaleIn 200ms ease-out',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },

      /* Keyframes */
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { transform: 'translateY(20px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          from: { transform: 'translateY(-10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          from: { transform: 'scale(0.95)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },

      /* Spacing */
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },

      /* Container */
      container: {
        center: true,
        padding: '1.5rem',
        screens: {
          sm: '640px',
          md: '768px',
          lg: '1024px',
          xl: '1280px',
        },
      },
    },
  },
  plugins: [],
};

export default config;
