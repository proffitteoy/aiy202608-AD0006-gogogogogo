"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

/**
 * 演示时把不想展示给评委的事件卡片临时藏起来。
 * 只在本地 localStorage 里记录，不动后端；换台机器 / 无痕窗口天然不隐藏。
 */

const STORAGE_KEY = "risktrace:hidden-events:v1";

function readStored(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((v): v is string => typeof v === "string");
  } catch {
    return [];
  }
}

function writeStored(ids: string[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    /* 存储不可用（隐私模式 / 配额），忽略——UI 状态仍然生效 */
  }
}

export function useHiddenEventIds() {
  const [ids, setIds] = useState<string[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setIds(readStored());
    setHydrated(true);
  }, []);

  const hide = useCallback((id: string) => {
    setIds((prev) => {
      if (prev.includes(id)) return prev;
      const next = [...prev, id];
      writeStored(next);
      return next;
    });
  }, []);

  const restoreAll = useCallback(() => {
    setIds([]);
    writeStored([]);
  }, []);

  const hiddenSet = useMemo(() => new Set(ids), [ids]);
  const isHidden = useCallback((id: string) => hiddenSet.has(id), [hiddenSet]);

  return { hiddenIds: ids, isHidden, hide, restoreAll, hydrated };
}
