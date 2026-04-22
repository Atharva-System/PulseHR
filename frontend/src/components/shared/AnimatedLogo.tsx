import { useEffect, useState } from "react";

interface AnimatedLogoProps {
  size?: "sm" | "md" | "lg";
  showText?: boolean;
  subtitle?: string;
  dark?: boolean;
}

export default function AnimatedLogo({
  size = "md",
  showText = true,
  subtitle,
  dark = false,
}: AnimatedLogoProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(t);
  }, []);

  const dims = { sm: 36, md: 44, lg: 56 }[size];
  const iconScale = { sm: 16, md: 20, lg: 28 }[size];
  const textSize = { sm: "text-sm", md: "text-base", lg: "text-2xl" }[size];
  const subSize = { sm: "text-[10px]", md: "text-xs", lg: "text-sm" }[size];

  return (
    <div className="flex items-center gap-3">
      {/* Animated icon container */}
      <div
        className="relative flex items-center justify-center rounded-xl transition-all duration-700 ease-out"
        style={{
          width: dims,
          height: dims,
          background:
            "linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #2563eb 100%)",
          backgroundSize: "200% 200%",
          animation: mounted ? "logoGradient 3s ease infinite" : "none",
          transform: mounted
            ? "scale(1) rotate(0deg)"
            : "scale(0.5) rotate(-10deg)",
          opacity: mounted ? 1 : 0,
          boxShadow: "0 4px 15px rgba(37, 99, 235, 0.3)",
        }}
      >
        {/* Pulse ring */}
        <div
          className="absolute inset-0 rounded-xl"
          style={{
            animation: mounted ? "logoPulse 2s ease-in-out infinite" : "none",
            border: "2px solid rgba(255,255,255,0.3)",
          }}
        />
        {/* Bot icon (SVG) */}
        <svg
          width={iconScale}
          height={iconScale}
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transition: "transform 0.5s ease",
            transform: mounted ? "scale(1)" : "scale(0)",
          }}
        >
          <path d="M12 8V4H8" />
          <rect width="16" height="12" x="4" y="8" rx="2" />
          <circle cx="9" cy="13" r="1" fill="white" stroke="none" />
          <circle cx="15" cy="13" r="1" fill="white" stroke="none" />
          <path d="M9 17h6" />
        </svg>
      </div>

      {/* Text */}
      {showText && (
        <div
          className="transition-all duration-500 ease-out"
          style={{
            transform: mounted ? "translateX(0)" : "translateX(-8px)",
            opacity: mounted ? 1 : 0,
            transitionDelay: "200ms",
          }}
        >
          <h1
            className={`font-bold tracking-tight ${textSize}`}
            style={{ color: dark ? "#f8fafc" : "#0f172a" }}
          >
            Pulse
            <span
              style={{
                background: "linear-gradient(135deg, #2563eb, #7c3aed)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              e
            </span>
            <span
              className="ml-1 inline-block align-super text-[9px] font-semibold tracking-wider uppercase rounded-full px-1.5 py-0.5"
              style={{
                background: "linear-gradient(135deg, #2563eb, #7c3aed)",
                color: "white",
                lineHeight: 1,
              }}
            >
              AI
            </span>
          </h1>
          {subtitle && (
            <p
              className={`${subSize} mt-0.5`}
              style={{ color: dark ? "rgba(248,250,252,0.6)" : "#64748b" }}
            >
              {subtitle}
            </p>
          )}
        </div>
      )}

      {/* Keyframe animations via inline style tag */}
      <style>{`
        @keyframes logoGradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes logoPulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.08); opacity: 0; }
        }
      `}</style>
    </div>
  );
}
