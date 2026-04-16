import React, { useState } from "react";

const STAR_LABELS = ["Terrible", "Poor", "Okay", "Good", "Excellent"];

export default function FeedbackStars({ onRate }) {
  const [hovered, setHovered] = useState(null);
  const [selected, setSelected] = useState(null);

  const handleSelect = (rating) => {
    setSelected(rating);
    setTimeout(() => onRate(String(rating)), 350);
  };

  const active = (n) =>
    selected !== null ? n <= selected : hovered !== null ? n <= hovered : false;

  return (
    <div className="fade-slide-in flex items-start gap-3">
      <div
        style={{
          background: "#fff",
          border: "1px solid #e2e8f0",
          borderRadius: "1.25rem",
          borderTopLeftRadius: "4px",
          padding: "18px 22px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
          maxWidth: "340px",
        }}
      >
        <p
          style={{
            margin: "0 0 4px",
            fontWeight: 700,
            color: "#1a3a7a",
            fontSize: "0.95em",
          }}
        >
          &#x1F31F; Rate your experience
        </p>
        <p
          style={{
            margin: "0 0 14px",
            fontSize: "0.78em",
            color: "#94a3b8",
          }}
        >
          Tap a star to leave feedback
        </p>

        <div style={{ display: "flex", gap: "6px", marginBottom: "12px" }}>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onMouseEnter={() => selected === null && setHovered(n)}
              onMouseLeave={() => selected === null && setHovered(null)}
              onClick={() => handleSelect(n)}
              title={STAR_LABELS[n - 1]}
              aria-label={STAR_LABELS[n - 1]}
              style={{
                background: "none",
                border: "none",
                cursor: selected !== null ? "default" : "pointer",
                fontSize: "2em",
                lineHeight: 1,
                padding: "2px 4px",
                transition: "transform 0.15s, filter 0.15s",
                transform: active(n) ? "scale(1.25)" : "scale(1)",
                filter: active(n) ? "none" : "grayscale(1) opacity(0.35)",
              }}
            >
              &#x2B50;
            </button>
          ))}
        </div>

        {(hovered !== null || selected !== null) && (
          <p
            style={{
              margin: 0,
              fontSize: "0.83em",
              color: selected !== null ? "#0f4ca3" : "#64748b",
              fontWeight: selected !== null ? 600 : 400,
              transition: "color 0.2s",
            }}
          >
            {STAR_LABELS[(selected ?? hovered) - 1]}
            {selected !== null && " — thank you!"}
          </p>
        )}
      </div>
    </div>
  );
}
