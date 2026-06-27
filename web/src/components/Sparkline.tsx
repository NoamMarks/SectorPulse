interface SparklineProps {
  values: Array<number | null>;
  width?: number;
  height?: number;
  /** Tailwind text color class controlling the stroke (via currentColor). */
  className?: string;
}

/**
 * Tiny inline SVG sparkline. Renders nothing meaningful when there are
 * fewer than two finite points. Color comes from `currentColor`.
 */
export default function Sparkline({
  values,
  width = 80,
  height = 24,
  className = '',
}: SparklineProps) {
  const points = values
    .map((v, i) => ({ v, i }))
    .filter((p): p is { v: number; i: number } =>
      typeof p.v === 'number' && Number.isFinite(p.v),
    );

  if (points.length < 2) {
    return (
      <svg
        width={width}
        height={height}
        className={className}
        aria-hidden="true"
        role="img"
      />
    );
  }

  const xs = values.length > 1 ? values.length - 1 : 1;
  const min = Math.min(...points.map((p) => p.v));
  const max = Math.max(...points.map((p) => p.v));
  const range = max - min || 1;

  const pad = 2;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;

  const coords = points.map((p) => {
    const x = pad + (p.i / xs) * innerW;
    // Invert y so larger values sit higher.
    const y = pad + (1 - (p.v - min) / range) * innerH;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const last = points[points.length - 1];
  const lastX = pad + (last.i / xs) * innerW;
  const lastY = pad + (1 - (last.v - min) / range) * innerH;

  // Up if the final point is at/above the first point.
  const rising = last.v >= points[0].v;
  const strokeClass = rising ? 'text-emerald-400' : 'text-red-400';

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={`${strokeClass} ${className}`}
      role="img"
      aria-label={rising ? 'Relative strength trending up' : 'Relative strength trending down'}
      preserveAspectRatio="none"
    >
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={lastX} cy={lastY} r={1.8} fill="currentColor" />
    </svg>
  );
}
