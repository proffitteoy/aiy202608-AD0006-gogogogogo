import styles from "./Sparkline.module.css";

type Props = {
  data: number[];
  width?: number;
  height?: number;
  strokeColor?: string;
  label?: string;
};

/**
 * 纯 SVG 迷你折线，无坐标轴、无 tooltip，只求信息密度。
 * 保持在 Server Component 使用（不引入客户端交互）。
 */
export function Sparkline({
  data,
  width = 120,
  height = 32,
  strokeColor = "var(--viz-1)",
  label,
}: Props) {
  if (data.length === 0) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1 || 1);

  const points = data
    .map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role={label ? "img" : "presentation"}
      aria-label={label}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
