"use client";

import { useEvidence } from "@/components/evidence/EvidenceContext";
import { formatScore, formatScoreInterval } from "@/lib/format";
import type { ResearchReport } from "@/lib/types";

import styles from "./ReportDocument.module.css";

type Props = {
  report: ResearchReport;
};

const LLM_SECTIONS = new Set(["overview", "recommendations", "risk-notes"]);
const STATUS_LABEL: Record<string, string> = {
  complete: "已完成",
  degraded: "降级",
};

function sectionIsDegraded(sectionId: string, reasons: string[]): boolean {
  return reasons.some((r) => r.startsWith(`${sectionId}_llm_unavailable`));
}

export function ReportDocument({ report }: Props) {
  const { open } = useEvidence();
  const reasons = report.degradationReasons ?? [];

  return (
    <article className={styles.article}>
      <section className={styles.summaryGrid} aria-label="报告摘要指标">
        <div className={styles.summaryCard} data-tone="score">
          <span className={styles.summaryLabel}>Rule 4</span>
          <span className={styles.summaryValue} data-numeric>
            {formatScore(report.event.score.calibratedScore)}
          </span>
        </div>
        <div className={styles.summaryCard} data-tone="confidence">
          <span className={styles.summaryLabel}>置信度</span>
          <span className={styles.summaryValue} data-numeric>
            {formatScore(report.event.score.confidence)}
          </span>
        </div>
        <div className={styles.summaryCard} data-tone="interval">
          <span className={styles.summaryLabel}>评分区间</span>
          <span className={styles.summaryValue} data-numeric>
            {formatScoreInterval(report.event.score.scoreInterval)}
          </span>
        </div>
        <div className={styles.summaryCard} data-tone="evidence">
          <span className={styles.summaryLabel}>冻结证据</span>
          <span className={styles.summaryValue} data-numeric>
            {report.snapshot.evidenceCount}
          </span>
        </div>
      </section>

      {reasons.length > 0 ? (
        <section className={styles.degradedBanner} aria-label="降级原因">
          <div className={styles.degradedHead}>
            <span className={styles.degradedIcon} aria-hidden="true">
              ⚠
            </span>
            <span>报告存在降级原因，结论仅供内部复核参考</span>
          </div>
          <ul className={styles.degradedList}>
            {reasons.map((reason) => (
              <li key={reason} className={styles.degradedItem}>
                {reason}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {report.sections.map((section, index) => {
        const isLlm = LLM_SECTIONS.has(section.id);
        const degraded = sectionIsDegraded(section.id, reasons);
        const source = isLlm ? (degraded ? "template" : "llm") : "template";
        return (
          <section
            key={section.id}
            className={styles.section}
            data-status={section.status}
          >
            <header className={styles.sectionHead}>
              <div className={styles.sectionLead}>
                <span className={styles.sectionIndex} aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h2 className={styles.sectionTitle}>{section.title}</h2>
              </div>
              <div className={styles.sectionMeta}>
                {isLlm ? (
                  <span
                    className={styles.sourceTag}
                    data-source={source}
                    title={
                      source === "llm"
                        ? "由 LLM 现场生成"
                        : "LLM 不可用，已回退模板"
                    }
                  >
                    {source === "llm" ? "AI 生成" : "模板回退"}
                  </span>
                ) : (
                  <span className={styles.sourceTag} data-source="template">
                    模板
                  </span>
                )}
                <span
                  className={styles.status}
                  data-status={section.status}
                >
                  {STATUS_LABEL[section.status] ?? section.status}
                </span>
              </div>
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
                        查看证据 · {item.evidenceIds.length}
                      </button>
                    ) : null}
                    {item.calculationIds.map((calculationId) => (
                      <span key={calculationId} className={styles.calcId}>
                        calc · {calculationId.slice(0, 8)}
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </article>
  );
}
