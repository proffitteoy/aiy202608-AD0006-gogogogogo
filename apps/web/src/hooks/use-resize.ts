"use client";

import { useEffect, type RefObject } from "react";

/**
 * 监听 ref.current 的尺寸变化。用于图表/画布类组件在容器尺寸改变时
 * 主动调用底层库的 resize/fitView，而不是依赖 window resize。
 */
export function useResize<T extends HTMLElement>(
  ref: RefObject<T | null>,
  callback: () => void,
): void {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new ResizeObserver(() => callback());
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref, callback]);
}
