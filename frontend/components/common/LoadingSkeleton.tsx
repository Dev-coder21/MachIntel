import React from "react";

interface SkeletonProps {
  height?: number | string;
  width?: number | string;
  count?: number;
  className?: string;
}

export const LoadingSkeleton: React.FC<SkeletonProps> = ({
  height = 20,
  width = "100%",
  count = 1,
  className = "",
}) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, width: "100%" }}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={className}
          style={{
            height,
            width,
            backgroundColor: "var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            position: "relative",
            overflow: "hidden",
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      ))}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 0.5;
          }
          50% {
            opacity: 0.9;
          }
        }
      `}</style>
    </div>
  );
};
