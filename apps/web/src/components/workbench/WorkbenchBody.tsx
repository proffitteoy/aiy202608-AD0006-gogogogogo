"use client";

import { useMemo } from "react";

import { DegradedBanner } from "@/components/ui/DegradedBanner";
import { ImpactMatrix } from "@/components/workbench/ImpactMatrix";
import { OpinionCluster } from "@/components/workbench/OpinionCluster";
import { Timeline } from "@/components/workbench/Timeline";
import { TransmissionGraph } from "@/components/workbench/TransmissionGraph";
import { WorkbenchGrid, WorkbenchPanel } from "@/components/workbench/WorkbenchGrid";
import { WorkbenchHeader } from "@/components/workbench/WorkbenchHeader";
import type { EventDetail } from "@/lib/types";

import { useDemoReveal } from "./DemoRevealContext";

type Props = {
  detail: EventDetail;
  warnings: string[];
};

const BLANK_SCORE: EventDetail["score"] = {
  status: "unavailable",
  rawScore: null,
  calibratedScore: null,
  confidence: null,
  scoreInterval: null,
  scoringVersion: null,
  calibrationVersion: null,
  calculationId: null,
  scoreCalculationId: null,
  degradationReasons: [],
};

const BLANK_AVAILABILITY: EventDetail["availability"] = {
  evidence: "available",
  opinions: "not_generated",
  transmission: "not_generated",
  impact: "not_generated",
  report: "not_generated",
};

function toBlank(detail: EventDetail): EventDetail {
  return {
    ...detail,
    score: BLANK_SCORE,
    timeline: [],
    opinions: [],
    graph: { nodes: [], edges: [] },
    impactMatrix: [],
    availability: BLANK_AVAILABILITY,
  };
}

export function WorkbenchBody({ detail, warnings }: Props) {
  const { revealed } = useDemoReveal();
  const view = useMemo(() => (revealed ? detail : toBlank(detail)), [revealed, detail]);

  const scoreWarning =
    view.score.status === "unavailable"
      ? "Rule 3/4 尚未产出"
      : view.score.status === "degraded"
        ? "评分记录处于降级状态"
        : null;
  // 未 reveal 时不给评委看警告条——评分未算是意料之中，不是异常
  const combinedWarning = revealed
    ? [...warnings, ...(scoreWarning ? [scoreWarning] : [])].join("；")
    : "";

  return (
    <>
      <WorkbenchHeader detail={view} sourceCount={detail.evidence.length} />

      {combinedWarning ? (
        <DegradedBanner message="部分研究产物不可用" hint={combinedWarning} />
      ) : null}

      <WorkbenchGrid
        timeline={
          <WorkbenchPanel
            id="timeline"
            eyebrow="TIMELINE"
            title="事件时间线"
            meta={`${view.timeline.length} 个时间点`}
          >
            <Timeline points={view.timeline} />
          </WorkbenchPanel>
        }
        clusters={
          <WorkbenchPanel
            id="clusters"
            eyebrow="OPINION ATTRIBUTION"
            title="观点归因"
            meta={`${view.opinions.length} 条`}
          >
            <OpinionCluster items={view.opinions} status={view.availability.opinions} />
          </WorkbenchPanel>
        }
        graph={
          <WorkbenchPanel
            id="graph"
            eyebrow="TRANSMISSION HYPOTHESES"
            title="传导假设"
            meta={`${view.graph.nodes.length} 节点 / ${view.graph.edges.length} 边`}
          >
            <TransmissionGraph
              graph={view.graph}
              status={view.availability.transmission}
              eventId={view.id}
            />
          </WorkbenchPanel>
        }
        impact={
          <WorkbenchPanel
            id="impact"
            eyebrow="IMPACT MATRIX"
            title="热力矩阵"
            meta={`${view.impactMatrix.length} 个对象`}
          >
            <ImpactMatrix rows={view.impactMatrix} status={view.availability.impact} />
          </WorkbenchPanel>
        }
      />
    </>
  );
}
