"use client";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { formatScore, formatScoreInterval } from "@/lib/format";
import type { ResearchReport } from "@/lib/types";

import styles from "./ReportDocument.module.css";

type Props = {
  report: ResearchReport;
};

export function ReportDocument({ report }: Props) {
  const { open } = useEvidence();

  return (
    <article className={styles.article}>
      <section className={styles.summaryGrid} aria-label="报告摘要指标">
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>Rule 4</span>
          <span className={styles.summaryValue} data-numeric>
            {formatScore(report.event.score.calibratedScore)}
          </span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>置信度</span>
          <span className={styles.summaryValue} data-numeric>
            {formatScore(report.event.score.confidence)}
          </span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>评分区间</span>
          <span className={styles.summaryValue} data-numeric>
            {formatScoreInterval(report.event.score.scoreInterval)}
          </span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryLabel}>冻结证据</span>
          <span className={styles.summaryValue} data-numeric>
            {report.snapshot.evidenceCount}
          </span>
        </div>
      </section>

      {report.sections.map((section) => (
        <section key={section.id} className={styles.section}>
          <header className={styles.sectionHead}>
            <h2 className={styles.sectionTitle}>{section.title}</h2>
            <span className={styles.status}>{section.status}</span>
          </header>

          <ul className={styles.list}>
            {section.items.map((item) => (
              <li key={item.id} className={styles.item}>
                <p className={styles.text}>{item.text}</p>
                <div className={styles.refs}>
                  {item.evidenceIds.length > 0 ? (
                    <button
                      type="button"
                      className={styles.evidenceBtn}
                      onClick={() => open(item.evidenceIds)}
                    >
                      查看证据 {item.evidenceIds.length}
                    </button>
                  ) : null}
                  {item.calculationIds.map((calculationId) => (
                    <span key={calculationId} className={styles.calcId}>
                      calculation_id · {calculationId}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </article>
  );
}
