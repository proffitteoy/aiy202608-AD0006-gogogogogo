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
import { AnalyzingBadge } from "@/components/ui/AnalyzingBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePanelReady } from "@/hooks/use-panel-ready";
import { useResize } from "@/hooks/use-resize";
import { chartPalette } from "@/lib/chart-theme";
import type {
  RiskLevel,
  TransmissionEdge,
  TransmissionGraph as GraphType,
  TransmissionNode,
  TransmissionNodeType,
} from "@/lib/types";

import styles from "./TransmissionGraph.module.css";

type Props = {
  graph: GraphType;
};

const nodeTypeLabel: Record<TransmissionNodeType, string> = {
  entity: "主体",
  sector: "板块",
  event: "事件",
};

const riskBorder: Record<RiskLevel, string> = {
  high: chartPalette.risk.high,
  mid: chartPalette.risk.mid,
  low: chartPalette.risk.low,
};

type CustomNodeData = {
  label: string;
  type: TransmissionNodeType;
  risk: RiskLevel;
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
      style={{ borderColor: riskBorder[nodeData.risk] }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className={styles.handle}
        isConnectable={false}
      />
      <span className={styles.nodeTag}>{nodeTypeLabel[nodeData.type]}</span>
      <span className={styles.nodeLabel}>{nodeData.label}</span>
      <Handle
        type="source"
        position={Position.Bottom}
        className={styles.handle}
        isConnectable={false}
      />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

/**
 * 分层布局：把 event 节点放中心，entity 节点在中环，sector 节点在外环。
 * 骨架合理，比纯圆形更能表达"从事件辐射到板块"的语义。
 */
function layoutNodes(nodes: TransmissionNode[]): Node[] {
  const cx = 360;
  const cy = 230;

  // 按类型 + risk 分层
  const entities = nodes.filter((n) => n.type === "entity");
  const sectors = nodes.filter((n) => n.type === "sector");
  const events = nodes.filter((n) => n.type === "event");

  const result: Node[] = [];

  events.forEach((n, i) => {
    result.push({
      id: n.id,
      type: "entity",
      position: { x: cx - 40, y: cy - 24 + i * 60 },
      data: { label: n.label, type: n.type, risk: n.risk },
    });
  });

  entities.forEach((n, i) => {
    const angle =
      (i / Math.max(entities.length, 1)) * Math.PI * 2 - Math.PI / 2;
    const r = 200;
    result.push({
      id: n.id,
      type: "entity",
      position: {
        x: cx + Math.cos(angle) * r - 48,
        y: cy + Math.sin(angle) * r - 24,
      },
      data: { label: n.label, type: n.type, risk: n.risk },
    });
  });

  sectors.forEach((n, i) => {
    const angle =
      (i / Math.max(sectors.length, 1)) * Math.PI * 2 - Math.PI / 3;
    const r = 320;
    result.push({
      id: n.id,
      type: "entity",
      position: {
        x: cx + Math.cos(angle) * r - 48,
        y: cy + Math.sin(angle) * r - 24,
      },
      data: { label: n.label, type: n.type, risk: n.risk },
    });
  });

  return result;
}

type EdgeVerdict = "pending" | "confirmed" | "rejected";

function buildEdgeStyle(
  weight: number,
  verdict: EdgeVerdict,
  selected: boolean,
): { stroke: string; strokeWidth: number; strokeDasharray?: string; opacity: number; transition: string } {
  const isConfirmed = verdict === "confirmed";
  const isRejected = verdict === "rejected";

  return {
    stroke: isConfirmed
      ? chartPalette.accent
      : isRejected
        ? chartPalette.risk.high
        : chartPalette.textTertiary,
    strokeWidth: (selected ? 2.5 : 1) + weight * 2.5,
    strokeDasharray: isConfirmed ? undefined : "5 4",
    opacity: isRejected ? 0.35 : 1,
    transition:
      "opacity 200ms cubic-bezier(0.16, 1, 0.3, 1), stroke-width 200ms, stroke 250ms",
  };
}

function toEdges(
  edges: TransmissionEdge[],
  verdicts: Record<string, EdgeVerdict>,
  selectedId: string | null,
): Edge[] {
  return edges.map((e) => {
    const verdict: EdgeVerdict =
      verdicts[e.id] ?? (e.confirmed ? "confirmed" : "pending");
    const style = buildEdgeStyle(e.weight, verdict, e.id === selectedId);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      animated: verdict === "confirmed",
      type: "smoothstep",
      style,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: style.stroke,
      },
      data: {
        evidenceIds: e.evidenceIds,
        weight: e.weight,
        verdict,
      },
    };
  });
}

function GraphInner({
  graph,
  wrapRef,
}: Props & { wrapRef: React.RefObject<HTMLDivElement | null> }) {
  const { open } = useEvidence();
  const { fitView } = useReactFlow();
  const [verdicts, setVerdicts] = useState<Record<string, EdgeVerdict>>({});
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  const onWrapResize = useCallback(() => {
    fitView({ padding: 0.25, duration: 200 });
  }, [fitView]);
  useResize(wrapRef, onWrapResize);

  const initialNodes = useMemo(() => layoutNodes(graph.nodes), [graph.nodes]);
  const rebuiltEdges = useMemo(
    () => toEdges(graph.edges, verdicts, selectedEdgeId),
    [graph.edges, verdicts, selectedEdgeId],
  );

  const [nodes, setNodes] = useNodesState(initialNodes);
  const [edges, setEdges] = useEdgesState(rebuiltEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(rebuiltEdges);
  }, [rebuiltEdges, setEdges]);

  const selectedEdge = selectedEdgeId
    ? graph.edges.find((e) => e.id === selectedEdgeId)
    : null;
  const selectedVerdict: EdgeVerdict = selectedEdgeId
    ? (verdicts[selectedEdgeId] ??
        (selectedEdge?.confirmed ? "confirmed" : "pending"))
    : "pending";
  const sourceLabel = selectedEdge
    ? graph.nodes.find((n) => n.id === selectedEdge.source)?.label
    : "";
  const targetLabel = selectedEdge
    ? graph.nodes.find((n) => n.id === selectedEdge.target)?.label
    : "";

  function setEdgeVerdict(next: EdgeVerdict) {
    if (!selectedEdgeId) return;
    setVerdicts((prev) => ({ ...prev, [selectedEdgeId]: next }));
  }

  const clearHighlight = useCallback(() => {
    setNodes((ns) =>
      ns.map((n) => ({
        ...n,
        data: { ...n.data, dimmed: false, highlighted: false },
      })),
    );
    setEdges((es) =>
      es.map((e) => ({
        ...e,
        style: { ...e.style, opacity: 1, strokeWidth: 1 + ((e.data as { weight: number }).weight ?? 0.5) * 2.5 },
      })),
    );
  }, [setNodes, setEdges]);

  const highlightNeighbors = useCallback(
    (nodeId: string) => {
      const linkedNodeIds = new Set<string>([nodeId]);
      graph.edges.forEach((e) => {
        if (e.source === nodeId || e.target === nodeId) {
          linkedNodeIds.add(e.source);
          linkedNodeIds.add(e.target);
        }
      });

      setNodes((ns) =>
        ns.map((n) => ({
          ...n,
          data: {
            ...n.data,
            dimmed: !linkedNodeIds.has(n.id),
            highlighted: n.id === nodeId,
          },
        })),
      );
      setEdges((es) =>
        es.map((e) => {
          const linked = e.source === nodeId || e.target === nodeId;
          const weight = (e.data as { weight: number }).weight ?? 0.5;
          return {
            ...e,
            style: {
              ...e.style,
              opacity: linked ? 1 : 0.15,
              strokeWidth: linked ? 2 + weight * 3 : 1 + weight * 2.5,
            },
          };
        }),
      );
    },
    [graph.edges, setNodes, setEdges],
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
        onNodeMouseEnter={(_, node) => highlightNeighbors(node.id)}
        onNodeMouseLeave={clearHighlight}
        onEdgeClick={(_, edge) => setSelectedEdgeId(edge.id)}
        onPaneClick={() => setSelectedEdgeId(null)}
        minZoom={0.4}
        maxZoom={2}
        panOnDrag
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background color="var(--border-subtle)" gap={24} size={1} />
        <Controls className={styles.controls} showInteractive={false} />
      </ReactFlow>

      {selectedEdge && (
        <div className={styles.edgePanel} role="dialog" aria-label="传导边操作">
          <div className={styles.edgePanelInfo}>
            <span className={styles.edgePanelLabel}>已选边</span>
            <span className={styles.edgePanelPath}>
              {sourceLabel}
              <span className={styles.edgePanelArrow} aria-hidden="true">
                →
              </span>
              {targetLabel}
            </span>
            <span className={styles.edgePanelWeight} data-numeric>
              权重 {(selectedEdge.weight * 100).toFixed(0)}%
            </span>
          </div>
          <div className={styles.edgePanelActions}>
            <button
              type="button"
              className={`${styles.edgeBtn} ${styles.edgeBtnConfirm}`}
              onClick={() => setEdgeVerdict("confirmed")}
              aria-pressed={selectedVerdict === "confirmed"}
            >
              <span aria-hidden="true">✓</span> 确认
            </button>
            <button
              type="button"
              className={`${styles.edgeBtn} ${styles.edgeBtnReject}`}
              onClick={() => setEdgeVerdict("rejected")}
              aria-pressed={selectedVerdict === "rejected"}
            >
              <span aria-hidden="true">✗</span> 拒绝
            </button>
            <button
              type="button"
              className={styles.edgeBtn}
              onClick={() => {
                if (selectedEdge.evidenceIds.length) {
                  open(selectedEdge.evidenceIds);
                }
              }}
              disabled={selectedEdge.evidenceIds.length === 0}
            >
              📄 证据
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
      )}
    </>
  );
}

export function TransmissionGraph({ graph }: Props) {
  const ready = usePanelReady(500);
  const wrapRef = useRef<HTMLDivElement>(null);

  if (!ready) {
    return (
      <>
        <AnalyzingBadge label="AI 推理传导路径 · 约 5 秒" />
        <Skeleton variant="graph" />
      </>
    );
  }

  return (
    <div ref={wrapRef} className={styles.wrap}>
      <ReactFlowProvider>
        <GraphInner graph={graph} wrapRef={wrapRef} />
      </ReactFlowProvider>
      <div className={styles.hint}>
        <span className={styles.hintDot} style={{ background: chartPalette.accent }} />
        <span>已确认（实线）</span>
        <span
          className={`${styles.hintDot} ${styles.hintDotDashed}`}
          style={{ color: chartPalette.textTertiary, opacity: 0.6 }}
        />
        <span>候选（虚线）</span>
      </div>
    </div>
  );
}
