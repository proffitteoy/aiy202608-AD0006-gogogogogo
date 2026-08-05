export interface ECharts {
  setOption(option: unknown): void;
  on(eventName: string, handler: (params: unknown) => void): void;
  resize(): void;
  dispose(): void;
}

export function init(
  element: HTMLElement,
  theme?: unknown,
  options?: { renderer?: "canvas" | "svg" },
): ECharts;
