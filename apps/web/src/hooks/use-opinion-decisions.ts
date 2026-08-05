"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * 每条观点的本地研判态。等后端补 `/api/opinions/{id}/decision` 后，
 * 这个 hook 内部换成 mutation 即可，调用方 API 不变。
 */
export type Decision = "include" | "exclude" | null;

export type OpinionState = {
  decision: Decision;
  note: string;
};

type OpinionStateMap = Record<string, OpinionState>;

const STORAGE_KEY = "risktrace:opinion-decisions:v1";
const EMPTY: OpinionState = { decision: null, note: "" };

function readAll(): OpinionStateMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === "object") return parsed as OpinionStateMap;
    return {};
  } catch {
    return {};
  }
}

function writeAll(map: OpinionStateMap) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* 存储不可用（隐私模式 / 配额），忽略——UI 状态仍然生效 */
  }
}

export function useOpinionDecisions() {
  const [map, setMap] = useState<OpinionStateMap>({});

  useEffect(() => {
    setMap(readAll());
  }, []);

  const getState = useCallback(
    (id: string): OpinionState => map[id] ?? EMPTY,
    [map],
  );

  const setDecision = useCallback((id: string, decision: Decision) => {
    setMap((prev) => {
      const cur = prev[id] ?? EMPTY;
      const nextEntry: OpinionState = { ...cur, decision };
      // 无决策 + 无笔记 → 从存储里删掉这个 key
      const shouldStore = nextEntry.decision !== null || nextEntry.note.length > 0;
      const next: OpinionStateMap = shouldStore
        ? { ...prev, [id]: nextEntry }
        : dropKey(prev, id);
      writeAll(next);
      return next;
    });
  }, []);

  const setNote = useCallback((id: string, note: string) => {
    setMap((prev) => {
      const cur = prev[id] ?? EMPTY;
      const nextEntry: OpinionState = { ...cur, note };
      const shouldStore = nextEntry.decision !== null || nextEntry.note.length > 0;
      const next: OpinionStateMap = shouldStore
        ? { ...prev, [id]: nextEntry }
        : dropKey(prev, id);
      writeAll(next);
      return next;
    });
  }, []);

  return { getState, setDecision, setNote };
}

function dropKey(map: OpinionStateMap, id: string): OpinionStateMap {
  if (!(id in map)) return map;
  const next: OpinionStateMap = {};
  for (const key of Object.keys(map)) {
    if (key !== id) next[key] = map[key];
  }
  return next;
}
