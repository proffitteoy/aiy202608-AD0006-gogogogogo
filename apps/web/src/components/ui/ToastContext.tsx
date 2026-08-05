"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

import styles from "./Toast.module.css";

export type ToastKind = "info" | "success" | "warning" | "error";

export interface Toast {
  id: string;
  kind: ToastKind;
  title: string;
  hint?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextValue {
  push: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_TTL_MS = 4000;

let toastCounter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback((toast: Omit<Toast, "id">) => {
    toastCounter += 1;
    const id = `t${toastCounter}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
  }, []);

  const value = useMemo(() => ({ push, dismiss }), [push, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastPortal toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

function ToastPortal({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  if (typeof document === "undefined") return null;
  if (toasts.length === 0) return null;

  return createPortal(
    <div className={styles.stack} role="region" aria-label="通知">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body,
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  useEffect(() => {
    const t = window.setTimeout(() => onDismiss(toast.id), DEFAULT_TTL_MS);
    return () => window.clearTimeout(t);
  }, [toast.id, onDismiss]);

  return (
    <div className={`${styles.toast} ${styles[`kind-${toast.kind}`]}`} role="status">
      <span className={styles.rail} aria-hidden="true" />
      <div className={styles.body}>
        <p className={styles.title}>{toast.title}</p>
        {toast.hint && <p className={styles.hint}>{toast.hint}</p>}
      </div>
      {toast.action && (
        <button
          type="button"
          className={styles.action}
          onClick={() => {
            toast.action?.onClick();
            onDismiss(toast.id);
          }}
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        className={styles.close}
        aria-label="关闭通知"
        onClick={() => onDismiss(toast.id)}
      >
        ×
      </button>
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
