/**
 * 数字、百分比、时间格式化工具。全部输出中文习惯格式。
 */

const numberFormatter = new Intl.NumberFormat("zh-CN");

export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

/**
 * +342% / -12% 带符号百分比
 */
export function formatSignedPercent(value: number, digits = 0): string {
  const sign = value > 0 ? "+" : value < 0 ? "" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/**
 * -0.72 情绪值 → 保留 2 位小数
 */
export function formatSentiment(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

/**
 * 0.68 → "0.68"
 */
export function formatRatio(value: number): string {
  return value.toFixed(2);
}

/**
 * ISO 时间 → "15:07"
 */
export function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/**
 * ISO 时间 → "2026-08-04 15:07"
 */
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const time = formatTime(iso);
  return `${date} ${time}`;
}

/**
 * "3 分钟前" / "2 小时前"
 */
export function formatRelative(iso: string, now = new Date()): string {
  const diff = Math.floor((now.getTime() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff} 秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}
