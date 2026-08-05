import { notFound } from "next/navigation";

import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { EvidenceProvider } from "@/components/evidence/EvidenceContext";
import { ToastProvider } from "@/components/ui/ToastContext";
import { ImpactMatrix } from "@/components/workbench/ImpactMatrix";
import { OpinionCluster } from "@/components/workbench/OpinionCluster";
import { Timeline } from "@/components/workbench/Timeline";
import { TransmissionGraph } from "@/components/workbench/TransmissionGraph";
import { WorkbenchGrid, WorkbenchPanel } from "@/components/workbench/WorkbenchGrid";
import { WorkbenchHeader } from "@/components/workbench/WorkbenchHeader";
import { DegradedBanner } from "@/components/ui/DegradedBanner";
import { loadEventDetail } from "@/lib/api/loaders";

import styles from "./page.module.css";

type Params = { id: string };
type SearchParams = { llm?: string };

export default async function EventWorkbenchPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams?: Promise<SearchParams>;
}) {
  const { id } = await params;
  const search = (await searchParams) ?? {};
  const loaded = await loadEventDetail(id);
  if (!loaded) notFound();

  const llmAvailable = search.llm !== "off" && loaded.data.llmAvailable;
  const detail = { ...loaded.data, llmAvailable };
  const usingMock = loaded.source === "mock";

  const sourceCount = detail.evidence.length;
  const avgSentiment =
    detail.timeline.length > 0
      ? detail.timeline.reduce((s, p) => s + p.sentiment, 0) / detail.timeline.length
      : 0;
  const reviewed = {
    done: detail.graph.edges.filter((e) => e.confirmed).length,
    total: detail.graph.edges.length,
  };

  return (
    <ToastProvider>
      <EvidenceProvider evidence={detail.evidence}>
        <div className={styles.layout}>
          <WorkbenchHeader
            detail={detail}
            sourceCount={sourceCount}
            avgSentiment={avgSentiment}
            reviewed={reviewed}
          />

          {(!detail.llmAvailable || usingMock) && (
            <DegradedBanner />
          )}

          <WorkbenchGrid
            timeline={
              <WorkbenchPanel
                id="timeline"
                eyebrow="TIMELINE"
                title="事件时间线"
                meta={`${detail.timeline.length} 个节点`}
              >
                <Timeline points={detail.timeline} />
              </WorkbenchPanel>
            }
            clusters={
              <WorkbenchPanel
                id="clusters"
                eyebrow="OPINION CLUSTERS"
                title="观点簇"
                meta={`${detail.clusters.length} 簇`}
              >
                <OpinionCluster
                  clusters={detail.clusters}
                  llmAvailable={detail.llmAvailable}
                />
              </WorkbenchPanel>
            }
            graph={
              <WorkbenchPanel
                id="graph"
                eyebrow="TRANSMISSION"
                title="传导路径"
                meta={`${detail.graph.nodes.length} 节点 / ${detail.graph.edges.length} 边`}
              >
                <TransmissionGraph graph={detail.graph} />
              </WorkbenchPanel>
            }
            impact={
              <WorkbenchPanel
                id="impact"
                eyebrow="IMPACT MATRIX"
                title="影响矩阵"
                meta={`${detail.impact.rows.length} × ${detail.impact.cols.length}`}
              >
                <ImpactMatrix matrix={detail.impact} />
              </WorkbenchPanel>
            }
          />
        </div>

        <EvidenceDrawer />
      </EvidenceProvider>
    </ToastProvider>
  );
}
