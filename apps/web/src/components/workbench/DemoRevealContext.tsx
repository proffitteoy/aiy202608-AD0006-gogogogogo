"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

/**
 * 演示模式遮罩：进入工作台时 revealed=false，所有分析产出（时间线 / 观点 / 传导 / 影响矩阵 / 评分）
 * 都以空态渲染；点击“运行分析”跑完 pipeline 后通过 reveal() 让真实数据一次性显现。
 * SSR 数据本身保留，不重复请求。
 */

type Ctx = {
  revealed: boolean;
  reveal: () => void;
};

const DemoRevealCtx = createContext<Ctx | null>(null);

export function DemoRevealProvider({ children }: { children: ReactNode }) {
  const [revealed, setRevealed] = useState(false);
  const reveal = useCallback(() => setRevealed(true), []);
  return (
    <DemoRevealCtx.Provider value={{ revealed, reveal }}>{children}</DemoRevealCtx.Provider>
  );
}

/**
 * 在 Provider 之外调用视为“已 reveal”（等价于关闭演示模式），
 * 这样其他不受演示遮罩的路由不需要额外的判断。
 */
export function useDemoReveal(): Ctx {
  const ctx = useContext(DemoRevealCtx);
  if (!ctx) return { revealed: true, reveal: () => {} };
  return ctx;
}
