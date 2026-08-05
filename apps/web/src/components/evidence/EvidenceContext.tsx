"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { EvidenceItem } from "@/lib/types";

type EvidenceStore = {
  evidenceById: Map<string, EvidenceItem>;
};

type EvidenceContextValue = {
  isOpen: boolean;
  activeIds: string[];
  items: EvidenceItem[];
  open: (ids: string[]) => void;
  close: () => void;
};

const EvidenceContext = createContext<EvidenceContextValue | null>(null);

type ProviderProps = {
  evidence: EvidenceItem[];
  children: ReactNode;
};

export function EvidenceProvider({ evidence, children }: ProviderProps) {
  const [activeIds, setActiveIds] = useState<string[]>([]);

  const store = useMemo<EvidenceStore>(() => {
    const map = new Map<string, EvidenceItem>();
    for (const item of evidence) map.set(item.id, item);
    return { evidenceById: map };
  }, [evidence]);

  const open = useCallback(
    (ids: string[]) => {
      if (ids.length === 0) return;
      setActiveIds(ids);
    },
    [],
  );

  const close = useCallback(() => {
    setActiveIds([]);
  }, []);

  const value = useMemo<EvidenceContextValue>(() => {
    const items = activeIds
      .map((id) => store.evidenceById.get(id))
      .filter((item): item is EvidenceItem => Boolean(item));
    return {
      isOpen: activeIds.length > 0,
      activeIds,
      items,
      open,
      close,
    };
  }, [activeIds, store, open, close]);

  return (
    <EvidenceContext.Provider value={value}>{children}</EvidenceContext.Provider>
  );
}

export function useEvidence(): EvidenceContextValue {
  const ctx = useContext(EvidenceContext);
  if (!ctx) {
    throw new Error("useEvidence must be used within EvidenceProvider");
  }
  return ctx;
}
