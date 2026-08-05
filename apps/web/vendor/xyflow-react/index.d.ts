import type {
  ComponentType,
  CSSProperties,
  Dispatch,
  ReactNode,
  SetStateAction,
} from "react";

export type Node<T = Record<string, unknown>> = {
  id: string;
  type?: string;
  position: { x: number; y: number };
  data: T;
  style?: CSSProperties;
};

export type Edge<T = Record<string, unknown>> = {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  data?: T;
  style?: CSSProperties;
  markerEnd?: { type: MarkerType; color?: string };
};

export type NodeProps<T = Record<string, unknown>> = { data: T };

export enum Position {
  Top = "top",
  Right = "right",
  Bottom = "bottom",
  Left = "left",
}

export enum MarkerType {
  Arrow = "arrow",
  ArrowClosed = "arrowclosed",
}

export const ReactFlow: ComponentType<Record<string, unknown> & { children?: ReactNode }>;
export const ReactFlowProvider: ComponentType<{ children?: ReactNode }>;
export const Background: ComponentType<Record<string, unknown>>;
export const Controls: ComponentType<Record<string, unknown>>;
export const Handle: ComponentType<Record<string, unknown>>;

export function useNodesState<T extends Node>(
  initial: T[],
): [T[], Dispatch<SetStateAction<T[]>>, (changes: unknown[]) => void];

export function useEdgesState<T extends Edge>(
  initial: T[],
): [T[], Dispatch<SetStateAction<T[]>>, (changes: unknown[]) => void];

export function useReactFlow(): {
  fitView(options?: { padding?: number; duration?: number }): void;
};
