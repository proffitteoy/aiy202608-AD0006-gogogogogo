"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 返回 [ref, progress]：progress 是元素相对视口的滚动进度。
 *
 * - 元素顶部到达视口顶部时：0
 * - 元素底部到达视口顶部时：1
 *
 * 用 requestAnimationFrame 节流；卸载时移除 listener。零依赖，替代
 * framer-motion 的 useScroll。
 */
export function useScrollProgress<T extends HTMLElement>(): [
  React.RefObject<T | null>,
  number,
] {
  const ref = useRef<T | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let raf = 0;
    let ticking = false;

    const update = () => {
      ticking = false;
      const node = ref.current;
      if (!node) return;
      const rect = node.getBoundingClientRect();
      const viewport = window.innerHeight || 1;
      // 元素总的可滚动距离：从顶部触底部触时 = rect.height
      const start = rect.top;
      const total = rect.height;
      if (total <= 0) return;
      // 0 = 元素顶到视口顶；1 = 元素底到视口顶
      const raw = -start / total;
      const clamped = Math.max(0, Math.min(1, raw));
      setProgress(clamped);
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      raf = requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return [ref, progress];
}
