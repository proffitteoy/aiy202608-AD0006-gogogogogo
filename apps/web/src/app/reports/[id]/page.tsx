import Link from "next/link";
import { notFound } from "next/navigation";

import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { EvidenceProvider } from "@/components/evidence/EvidenceContext";
import { ReportDocument } from "@/components/reports/ReportDocument";
import { DegradedBanner } from "@/components/ui/DegradedBanner";
import { formatDateTime, formatEventStatus } from "@/lib/format";
import { loadReportDetail } from "@/lib/api/loaders";

import styles from "./page.module.css";

type Params = { id: string };

export default async function ReportPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const loaded = await loadReportDetail(id);

  if (loaded.status === "not_found") {
    notFound();
  }

  if (loaded.status === "unavailable") {
    return (
      <main className={styles.errorPage}>
        <p className="eyebrow">REPORT</p>
        <h1>报告暂不可用</h1>
        <p>{loaded.reason}，页面未回退到本地样例。</p>
      </main>
    );
  }

  const report = loaded.data;
  const degradationHint =
    report.degradationReasons.length > 0
      ? report.degradationReasons.join("；")
      : "部分结构化产物未生成，报告保持显式降级。";

  return (
    <EvidenceProvider evidence={report.evidence}>
      <main className={styles.page}>
        <div className={styles.shell}>
          <nav className={styles.topbar} aria-label="报告导航">
            <Link href="/">← 返回总览</Link>
            <Link href={`/event/${report.event.id}`}>回到事件工作台</Link>
          </nav>

          <header className={styles.hero}>
            <p className="eyebrow">REPORT / HTML</p>
            <h1 className={styles.title}>{report.title}</h1>
            <p className={styles.summary}>{report.summary}</p>
            <div className={styles.meta}>
              <span className={styles.metaCell}>
                {formatEventStatus(report.event.status)}
              </span>
              <span className={styles.metaCell}>
                snapshot · {formatDateTime(report.snapshot.snapshotAt)}
              </span>
              <span className={styles.metaCell}>
                analysis_version · {report.snapshot.analysisVersion}
              </span>
              <span className={styles.metaCell}>
                render_engine · {report.renderEngine}
              </span>
              <span className={styles.metaCell}>
                created_at · {formatDateTime(report.createdAt)}
              </span>
            </div>
          </header>

          {report.status === "degraded" ? (
            <DegradedBanner
              message="报告包含降级内容"
              hint={degradationHint}
            />
          ) : null}

          <ReportDocument report={report} />
        </div>

        <EvidenceDrawer />
      </main>
    </EvidenceProvider>
  );
}
