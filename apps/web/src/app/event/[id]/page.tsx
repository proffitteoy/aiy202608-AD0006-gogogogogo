import { notFound } from "next/navigation";

import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { EvidenceProvider } from "@/components/evidence/EvidenceContext";
import { Header } from "@/components/ui/Header";
import { DegradedBanner } from "@/components/ui/DegradedBanner";
import { OpinionCluster } from "@/components/workbench/OpinionCluster";
import { Timeline } from "@/components/workbench/Timeline";
import { TransmissionGraph } from "@/components/workbench/TransmissionGraph";
import { WorkbenchGrid, WorkbenchPanel } from "@/components/workbench/WorkbenchGrid";
import { WorkbenchHeader } from "@/components/workbench/WorkbenchHeader";
import { loadEventDetail } from "@/lib/api/loaders";
import type { Availability } from "@/lib/types";

import styles from "./page.module.css";

type Params = { id: string };

function UnavailableState({
  status,
  label,
}: {
  status: Availability;
  label: string;
}) {
  const degraded = status === "degraded";
  return (
    <div className={styles.unavailable} role="status">
      <strong>{degraded ? `${label}接口不可用` : `${label}尚未生成`}</strong>
      <span>
        {degraded ? "其余可用数据继续展示。" : "当前后端没有可验证的对应产物。"}
      </span>
    </div>
  );
}

export default async function EventWorkbenchPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const loaded = await loadEventDetail(id);
  if (loaded.status === "not_found") notFound();

  if (loaded.status === "unavailable") {
    return (
      <>
        <Header />
        <main className={styles.errorPage}>
          <p className="eyebrow">EVENT WORKSPACE</p>
          <h1>事件工作台暂不可用</h1>
          <p>{loaded.reason}，页面未回退到本地样例。</p>
        </main>
      </>
    );
  }

  const detail = loaded.data;
  const scoreWarning =
    detail.score.status === "unavailable"
      ? "Rule 3/4 尚未产出"
      : detail.score.status === "degraded"
        ? "评分记录处于降级状态"
        : null;
  const warning = [...loaded.warnings, ...(scoreWarning ? [scoreWarning] : [])].join("；");

  return (
    <EvidenceProvider evidence={detail.evidence}>
      <div className={styles.layout}>
        <WorkbenchHeader detail={detail} sourceCount={detail.evidence.length} />

        {warning ? (
          <DegradedBanner message="部分研究产物不可用" hint={warning} />
        ) : null}

        <WorkbenchGrid
          timeline={
            <WorkbenchPanel
              id="timeline"
              eyebrow="TIMELINE"
              title="文档时间线"
              meta={`${detail.timeline.length} 个时间桶`}
            >
              <Timeline points={detail.timeline} />
            </WorkbenchPanel>
          }
          clusters={
            <WorkbenchPanel
              id="clusters"
              eyebrow="OPINION ATTRIBUTION"
              title="观点归因"
              meta={`${detail.opinions.length} 条`}
            >
              <OpinionCluster
                items={detail.opinions}
                status={detail.availability.opinions}
              />
            </WorkbenchPanel>
          }
          graph={
            <WorkbenchPanel
              id="graph"
              eyebrow="TRANSMISSION HYPOTHESES"
              title="传导假设"
              meta={`${detail.graph.nodes.length} 节点 / ${detail.graph.edges.length} 边`}
            >
              <TransmissionGraph
                graph={detail.graph}
                status={detail.availability.transmission}
              />
            </WorkbenchPanel>
          }
          impact={
            <WorkbenchPanel
              id="impact"
              eyebrow="IMPACT MATRIX"
              title="影响矩阵"
              meta="unavailable"
            >
              <UnavailableState status={detail.availability.impact} label="影响矩阵" />
            </WorkbenchPanel>
          }
        />
      </div>

      <EvidenceDrawer />
    </EvidenceProvider>
  );
}
