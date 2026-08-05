import styles from "./HighlightedText.module.css";

type Props = {
  text: string;
  highlights: string[];
};

/**
 * 只做纯文本高亮：把 highlights 里出现的原始子串包一层 <mark>。
 * 不解析 HTML，不 dangerouslySetInnerHTML —— 避免 XSS。
 */
export function HighlightedText({ text, highlights }: Props) {
  if (highlights.length === 0) {
    return <>{text}</>;
  }

  const pattern = highlights
    .map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .filter((s) => s.length > 0)
    .join("|");

  if (!pattern) return <>{text}</>;

  const parts = text.split(new RegExp(`(${pattern})`, "g"));

  return (
    <>
      {parts.map((part, i) =>
        highlights.includes(part) ? (
          <mark key={i} className={styles.mark}>
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
