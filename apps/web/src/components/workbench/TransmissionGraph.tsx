"use client";

import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { useResize } from "@/hooks/use-resize";
import { chartPalette } from "@/lib/chart-theme";
import { formatScore } from "@/lib/format";
import type {
  Availability,
  TransmissionEdge,
  TransmissionGraph as GraphType,
  TransmissionNode,
  TransmissionNodeType,
} from "@/lib/types";

import styles from "./TransmissionGraph.module.css";

type Props = {
  graph: GraphType;
  status: Availability;
  eventId: string;
};

const nodeTypeLabel: Record<TransmissionNodeType, string> = {
  entity: "主体",
  sector: "板块",
  event: "事件",
};

const nodeBorder: Record<TransmissionNodeType, string> = {
  entity: chartPalette.viz[0],
  sector: chartPalette.viz[3],
  event: chartPalette.accent,
};

type CustomNodeData = {
  label: string;
  type: TransmissionNodeType;
  dimmed?: boolean;
  highlighted?: boolean;
};

function EntityNode({ data }: NodeProps) {
  const nodeData = data as CustomNodeData;
  const classes = [styles.node];
  if (nodeData.dimmed) classes.push(styles.nodeDimmed);
  if (nodeData.highlighted) classes.push(styles.nodeHighlighted);

  return (
    <div
      className={classes.join(" ")}
      style={{ borderColor: nodeBorder[nodeData.type] }}
    >
      <Handle type="target" position={Position.Top} className={styles.handle} />
      <span className={styles.nodeTag}>{nodeTypeLabel[nodeData.type]}</span>
      <span className={styles.nodeLabel}>{nodeData.label}</span>
      <Handle type="source" position={Position.Bottom} className={styles.handle} />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

function layoutNodes(nodes: TransmissionNode[]): Node[] {
  const centerX = 360;
  const centerY = 230;
  const grouped = {
    event: nodes.filter((node) => node.type === "event"),
    entity: nodes.filter((node) => node.type === "entity"),
    sector: nodes.filter((node) => node.type === "sector"),
  };
  const result: Node[] = [];

  grouped.event.forEach((node, index) => {
    result.push({
      id: node.id,
      type: "entity",
      position: { x: centerX - 48, y: centerY - 24 + index * 64 },
      data: { label: node.label, type: node.type },
    });
  });

  for (const [type, radius] of [
    ["entity", 200],
    ["sector", 320],
  ] as const) {
    grouped[type].forEach((node, index) => {
      const angle =
        (index / Math.max(grouped[type].length, 1)) * Math.PI * 2 - Math.PI / 2;
      result.push({
        id: node.id,
        type: "entity",
        position: {
          x: centerX + Math.cos(angle) * radius - 48,
          y: centerY + Math.sin(angle) * radius - 24,
        },
        data: { label: node.label, type: node.type },
      });
    });
  }

  return result;
}

function edgeStyle(edge: TransmissionEdge, selected: boolean) {
  const confirmed = edge.status.toLowerCase() === "confirmed";
  const rejected = edge.status.toLowerCase() === "rejected";
  return {
    stroke: confirmed
      ? chartPalette.accent
      : rejected
        ? chartPalette.risk.high
        : chartPalette.textTertiary,
    strokeWidth: (selected ? 2.5 : 1) + edge.confidence * 2.5,
    strokeDasharray: confirmed ? undefined : "5 4",
    opacity: rejected ? 0.35 : 1,
    transition: "opacity 180ms, stroke-width 180ms, stroke 180ms",
  };
}

function toEdges(edges: TransmissionEdge[], selectedId: string | null): Edge[] {
  return edges.map((edge) => {
    const style = edgeStyle(edge, edge.id === selectedId);
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      animated: edge.status.toLowerCase() === "confirmed",
      type: "smoothstep",
      style,
      markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
      data: { confidence: edge.confidence },
    };
  });
}

function GraphInner({
  graph,
  wrapRef,
}: {
  graph: GraphType;
  wrapRef: React.RefObject<HTMLDivElement | null>;
}) {
  const { open } = useEvidence();
  const { fitView } = useReactFlow();
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const initialNodes = useMemo(() => layoutNodes(graph.nodes), [graph.nodes]);
  const rebuiltEdges = useMemo(
    () => toEdges(graph.edges, selectedEdgeId),
    [graph.edges, selectedEdgeId],
  );
  const [nodes, setNodes] = useNodesState(initialNodes);
  const [edges, setEdges] = useEdgesState(rebuiltEdges);

  useResize(
    wrapRef,
    useCallback(() => fitView({ padding: 0.25, duration: 200 }), [fitView]),
  );

  useEffect(() => setNodes(initialNodes), [initialNodes, setNodes]);
  useEffect(() => setEdges(rebuiltEdges), [rebuiltEdges, setEdges]);

  const selectedEdge = selectedEdgeId
    ? graph.edges.find((edge) => edge.id === selectedEdgeId)
    : undefined;
  const sourceLabel = selectedEdge
    ? graph.nodes.find((node) => node.id === selectedEdge.source)?.label
    : undefined;
  const targetLabel = selectedEdge
    ? graph.nodes.find((node) => node.id === selectedEdge.target)?.label
    : undefined;

  const clearHighlight = useCallback(() => {
    setNodes((current) =>
      current.map((node) => ({
        ...node,
        data: { ...node.data, dimmed: false, highlighted: false },
      })),
    );
    setEdges(rebuiltEdges);
  }, [rebuiltEdges, setEdges, setNodes]);

  const highlightNeighbors = useCallback(
    (nodeId: string) => {
      const linked = new Set<string>([nodeId]);
      graph.edges.forEach((edge) => {
        if (edge.source === nodeId || edge.target === nodeId) {
          linked.add(edge.source);
          linked.add(edge.target);
        }
      });
      setNodes((current) =>
        current.map((node) => ({
          ...node,
          data: {
            ...node.data,
            dimmed: !linked.has(node.id),
            highlighted: node.id === nodeId,
          },
        })),
      );
      setEdges((current) =>
        current.map((edge) => ({
          ...edge,
          style: {
            ...edge.style,
            opacity: edge.source === nodeId || edge.target === nodeId ? 1 : 0.15,
          },
        })),
      );
    },
    [graph.edges, setEdges, setNodes],
  );

  return (
    <>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        onNodeMouseEnter={(_event: unknown, node: Node) => highlightNeighbors(node.id)}
        onNodeMouseLeave={clearHighlight}
        onEdgeClick={(_event: unknown, edge: Edge) => setSelectedEdgeId(edge.id)}
        onPaneClick={() => setSelectedEdgeId(null)}
        minZoom={0.4}
        maxZoom={2}
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background color="var(--border-subtle)" gap={24} size={1} />
        <Controls className={styles.controls} showInteractive={false} />
      </ReactFlow>

      {selectedEdge ? (
        <div className={styles.edgePanel} role="dialog" aria-label="传导假设详情">
          <div className={styles.edgePanelInfo}>
            <span className={styles.edgePanelPath}>
              {sourceLabel ?? "未解析主体"}
              <span className={styles.edgePanelArrow} aria-hidden="true">→</span>
              {targetLabel ?? "未解析主体"}
            </span>
            <span className={styles.edgePanelWeight} data-numeric>
              置信度 {formatScore(selectedEdge.confidence)}
            </span>
            <span className={styles.edgePanelMechanism}>{selectedEdge.mechanism}</span>
            <span className={styles.edgePanelMeta}>
              {selectedEdge.direction} · {selectedEdge.horizon} · {selectedEdge.status}
            </span>
          </div>
          <div className={styles.edgePanelActions}>
            <button
              type="button"
              className={styles.edgeBtn}
              onClick={() => open(selectedEdge.evidenceIds)}
              disabled={selectedEdge.evidenceIds.length === 0}
            >
              证据
            </button>
            <button
              type="button"
              className={`${styles.edgeBtn} ${styles.edgeBtnClose}`}
              onClick={() => setSelectedEdgeId(null)}
              aria-label="关闭"
            >
              ×
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}

export function TransmissionGraph({ graph, status, eventId }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const normalizeGenerateError = useCallback((message: string) => {
    if (message === "Not Found" || message.includes("HTTP 404")) {
      return "当前 API 进程未暴露传导生成接口，请确认后端已重启到当前仓库版本。";
    }
    if (
      message.includes("RISKTRACE_LLM_API_KEY") ||
      message.includes("LLM API Key")
    ) {
      return "当前环境未配置可用的 LLM API Key，请检查 .env 中的 RISKTRACE_LLM_API_KEY。";
    }
    if (
      message.includes("All connection attempts failed") ||
      message.includes("LLM 请求失败") ||
      message.includes("当前 LLM 服务不可达")
    ) {
      return "当前 LLM 服务不可达，传导候选暂时无法生成；事件工作台其余部分仍可继续使用。";
    }
    return message;
  }, []);

  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    setGenError(null);
    try {
      const res = await fetch(
        `/api/backend/events/${encodeURIComponent(eventId)}/transmission/generate`,
        { method: "POST" },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      window.location.reload();
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : String(err);
      setGenError(normalizeGenerateError(rawMessage));
    } finally {
      setGenerating(false);
    }
  }, [eventId, normalizeGenerateError]);

  if (status !== "available" || graph.edges.length === 0) {
    return (
      <div className={styles.empty} role="status">
        <strong>{status === "degraded" ? "传导接口不可用" : "传导假设尚未生成"}</strong>
        <span>Agent 2 Analyze 没有可验证的传导候选。</span>
        {status !== "degraded" && (
          <button
            type="button"
            className={styles.generateBtn}
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? "生成中..." : "生成传导假设"}
          </button>
        )}
        {genError && <span className={styles.genError}>{genError}</span>}
      </div>
    );
  }

  return (
    <div ref={wrapRef} className={styles.wrap}>
      <ReactFlowProvider>
        <GraphInner graph={graph} wrapRef={wrapRef} />
      </ReactFlowProvider>
      <div className={styles.hint}>
        <span className={styles.hintDot} style={{ background: chartPalette.accent }} />
        <span>已确认</span>
        <span className={`${styles.hintDot} ${styles.hintDotDashed}`} />
        <span>候选</span>
      </div>
    </div>
  );
}
