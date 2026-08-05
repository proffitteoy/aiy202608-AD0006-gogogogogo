"use client";

import { useEffect, useState } from "react";

/**
 * 检测组件是否位于 `data-theme="dark"` 作用域内。
 * 用 closest() 沿 DOM 树上溯，找到最近的 data-theme 属性。
 * 无 SSR 分歧：初始 return "light"，effect 后校正。
 */
export function useIsDark(ref: React.RefObject<Element | null>): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const themed = node.closest("[data-theme]") as HTMLElement | null;
    setIsDark(themed?.dataset.theme === "dark");
  }, [ref]);

  return isDark;
}
