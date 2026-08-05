"use client";

/**
 * 已下线：原先用来模拟 "AI 分析中" 的骨架延时。
 * 接后端后真实数据已经到达浏览器，不需要再假等，直接返回 ready = true。
 */
export function usePanelReady(_delayMs = 0): boolean {
  return true;
}
