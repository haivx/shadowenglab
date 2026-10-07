import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Token là hex nên màu map thẳng sang var(--x), không có wrapper hsl().
// Hệ quả: không dùng modifier độ mờ kiểu `bg-primary/90` (UI-SPEC Token Implementation Map mục 4).
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
          text: "var(--destructive-text)",
          soft: "var(--destructive-soft)",
          border: "var(--destructive-border)",
        },
        success: {
          DEFAULT: "var(--success)",
          text: "var(--success-text)",
          soft: "var(--success-soft)",
        },
        warning: {
          soft: "var(--warning-soft)",
          border: "var(--warning-border)",
          text: "var(--warning-text)",
        },
        video: "var(--video-bg)",
        original: {
          DEFAULT: "var(--original)",
          text: "var(--original-text)",
          soft: "var(--original-soft)",
        },
        you: {
          DEFAULT: "var(--you)",
          text: "var(--you-text)",
          soft: "var(--you-soft)",
        },
        score: {
          good: {
            DEFAULT: "var(--score-good)",
            text: "var(--score-good-text)",
            soft: "var(--score-good-soft)",
          },
          ok: {
            DEFAULT: "var(--score-ok)",
            text: "var(--score-ok-text)",
            soft: "var(--score-ok-soft)",
          },
          bad: {
            DEFAULT: "var(--score-bad)",
            text: "var(--score-bad-text)",
            soft: "var(--score-bad-soft)",
          },
          unrated: {
            DEFAULT: "var(--score-unrated)",
            text: "var(--score-unrated-text)",
          },
        },
        recording: "var(--recording)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
        ipa: ["var(--font-ipa)"],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      // Thanh tiến độ không phần trăm (Progress indeterminate); tắt khi giảm chuyển động.
      keyframes: {
        "progress-slide": {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(250%)" },
        },
      },
      animation: {
        "progress-slide": "progress-slide 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
