// The exact shield-with-rising-bars mark from the original prototype
// (viewBox "0 0 58 62", navy shield fill #103A6B, cyan stroke #17B6E0,
// three bars in cyan/light-cyan/white representing a trend improving).
// Reused everywhere the product needs its mark: sidebar, auth screens,
// public report header, PDF reports.
//
// variant="outline" is the lighter mark the prototype uses specifically
// in the DataScore card header - stroke-only, no fill, no bars (see
// DataScoreHeader.jsx) - kept here rather than duplicated since it's
// the same path data, just styled differently.
export default function Logo({ size = 24, variant = "filled" }) {
  const height = Math.round((size * 62) / 58);

  if (variant === "outline") {
    return (
      <svg width={size} height={height} viewBox="0 0 58 62" fill="none">
        <path
          d="M29 2 L52 11 C52 30 46 47 29 60 C12 47 6 30 6 11 Z"
          fill="none"
          stroke="#17B6E0"
          strokeWidth="3"
        />
      </svg>
    );
  }

  return (
    <svg width={size} height={height} viewBox="0 0 58 62" fill="none">
      <path
        d="M29 2 L52 11 C52 30 46 47 29 60 C12 47 6 30 6 11 Z"
        fill="#103A6B"
        stroke="#17B6E0"
        strokeWidth="2"
      />
      <rect x="20" y="34" width="5.5" height="10" rx="1.5" fill="#17B6E0" />
      <rect x="27.5" y="28" width="5.5" height="16" rx="1.5" fill="#3DD3F0" />
      <rect x="35" y="20" width="5.5" height="24" rx="1.5" fill="#FFFFFF" />
    </svg>
  );
}
