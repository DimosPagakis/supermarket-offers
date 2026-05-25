import { formatPrice } from "@/lib/format";
import type { PriceHistoryPoint } from "@/lib/types";

type Props = {
  history: PriceHistoryPoint[];
  currency?: string;
};

/**
 * Tiny SVG line chart. We deliberately skip Recharts/Chart.js: a single
 * sparkline doesn't earn its keep against a 50KB dependency. If we add
 * a second chart type we'll reconsider.
 */
export function PriceHistoryChart({ history, currency = "EUR" }: Props) {
  if (history.length === 0) return null;
  const width = 560;
  const height = 180;
  const padding = { top: 16, right: 16, bottom: 28, left: 48 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const prices = history.map((h) => h.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const stepX = history.length > 1 ? innerW / (history.length - 1) : 0;
  const points = history.map((h, i) => {
    const x = padding.left + i * stepX;
    const y = padding.top + (1 - (h.price - min) / range) * innerH;
    return { x, y, point: h };
  });

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" ");

  const areaPath =
    points.length > 1
      ? `${path} L${points[points.length - 1].x.toFixed(1)},${(padding.top + innerH).toFixed(1)} L${points[0].x.toFixed(1)},${(padding.top + innerH).toFixed(1)} Z`
      : "";

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
        Ιστορικό τιμής
      </h2>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        role="img"
        aria-label="Διάγραμμα ιστορικού τιμής"
      >
        <line
          x1={padding.left}
          y1={padding.top + innerH}
          x2={padding.left + innerW}
          y2={padding.top + innerH}
          stroke="currentColor"
          className="text-zinc-200 dark:text-zinc-700"
        />
        <text
          x={padding.left - 8}
          y={padding.top + 4}
          textAnchor="end"
          className="fill-zinc-500 text-[10px]"
        >
          {formatPrice(max, currency)}
        </text>
        <text
          x={padding.left - 8}
          y={padding.top + innerH + 4}
          textAnchor="end"
          className="fill-zinc-500 text-[10px]"
        >
          {formatPrice(min, currency)}
        </text>

        {areaPath && (
          <path
            d={areaPath}
            className="fill-emerald-500/10"
            stroke="none"
          />
        )}
        <path
          d={path}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className="text-emerald-600"
        />
        {points.map((p) => (
          <circle
            key={p.point.date}
            cx={p.x}
            cy={p.y}
            r={3}
            className="fill-emerald-600"
          />
        ))}
        {points.length > 0 && (
          <>
            <text
              x={points[0].x}
              y={height - 8}
              textAnchor="start"
              className="fill-zinc-500 text-[10px]"
            >
              {points[0].point.date}
            </text>
            <text
              x={points[points.length - 1].x}
              y={height - 8}
              textAnchor="end"
              className="fill-zinc-500 text-[10px]"
            >
              {points[points.length - 1].point.date}
            </text>
          </>
        )}
      </svg>
    </div>
  );
}
