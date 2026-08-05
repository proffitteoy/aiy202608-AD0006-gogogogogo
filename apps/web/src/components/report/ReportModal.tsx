"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { createPortal } from "react-dom";

import { useOpinionDecisions } from "@/hooks/use-opinion-decisions";
import { ImpactMatrix } from "@/components/workbench/ImpactMatrix";
import { TransmissionGraph } from "@/components/workbench/TransmissionGraph";
import {
  formatDateTime,
  formatScore,
  formatScoreInterval,
} from "@/lib/format";
import type { EventDetail, OpinionAttribution } from "@/lib/types";

import styles from "./ReportModal.module.css";

type Props = {
  detail: EventDetail;
  onClose: () => void;
};

const STANCE_LABELS: Record<string, string> = {
  bullish: "看多",
  bearish: "看空",
  wait: "观望",
  neutral: "中性",
  positive: "正面",
  negative: "负面",
};

const CLAIM_TYPE_LABELS: Record<string, string> = {
  opinion: "观点",
  speculation: "推测",
  fact: "事实陈述",
  question: "疑问",
};

const SOURCE_TIER_LABELS: Record<string, string> = {
  authoritative: "权威事实源",
  media: "专业媒体",
  social: "社交讨论",
  market: "市场行情",
};

function localize(raw: string, dict: Record<string, string>): string {
  return dict[raw.toLowerCase()] ?? raw;
}

export function ReportModal({ detail, onClose }: Props) {
  const { getState } = useOpinionDecisions();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  const groupedOpinions = useMemo(() => {
    const include: OpinionAttribution[] = [];
    const exclude: OpinionAttribution[] = [];
    const undecided: OpinionAttribution[] = [];
    for (const item of detail.opinions) {
      const decision = getState(item.id).decision;
      if (decision === "include") include.push(item);
      else if (decision === "exclude") exclude.push(item);
      else undecided.push(item);
    }
    return { include, exclude, undecided };
  }, [detail.opinions, getState]);

  const groupedEvidence = useMemo(() => {
    const groups: Record<string, typeof detail.evidence> = {
      authoritative: [],
      media: [],
      social: [],
      market: [],
    };
    for (const e of detail.evidence) {
      const bucket = groups[e.sourceTier] ?? groups.social;
      bucket.push(e);
    }
    return groups;
  }, [detail.evidence]);

  const now = new Date();
  const reportId = `RTC-${detail.id.slice(0, 8).toUpperCase()}-${now
    .toISOString()
    .slice(0, 10)
    .replace(/-/g, "")}`;

  // portal 到 body 顶层，避开父级 overflow: hidden 的影响
  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className={styles.scrim}
      role="dialog"
      aria-modal="true"
      aria-label="事件研究报告预览"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className={styles.toolbarShell}>
        <div className={styles.toolbar}>
          <span className={styles.toolbarLabel}>报告预览</span>
          <div className={styles.toolbarActions}>
            <button
              type="button"
              className={styles.actionBtn}
              onClick={handlePrint}
            >
              <span aria-hidden="true">⎙</span> 打印 / 导出 PDF
            </button>
            <button
              ref={closeRef}
              type="button"
              className={styles.closeBtn}
              onClick={onClose}
              aria-label="关闭报告预览"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      <article className={styles.paper} data-report-root>
        <header className={styles.paperHead}>
          <div className={styles.eyebrowRow}>
            <span className={styles.brand}>◆ RiskTrace</span>
            <span className={styles.reportId} data-numeric>
              {reportId}
            </span>
          </div>
          <h1 className={styles.paperTitle}>{detail.title}</h1>
          <p className={styles.paperMeta}>
            <span>首次发布 {formatDateTime(detail.publishedAt)}</span>
            <span className={styles.metaSep}>·</span>
            <span>生成时间 {formatDateTime(now.toISOString())}</span>
            <span className={styles.metaSep}>·</span>
            <span>研判范围 · 本地研究快照</span>
          </p>
        </header>

        <section className={styles.summary}>
          <h2 className={styles.h2}>一、事件要点</h2>
          <div className={styles.summaryGrid}>
            <ScorePill label="Rule 3 基础分" value={formatScore(detail.score.rawScore)} />
            <ScorePill label="Rule 4 校准分" value={formatScore(detail.score.calibratedScore)} />
            <ScorePill label="置信度" value={formatScore(detail.score.confidence)} />
            <ScorePill label="评分区间" value={formatScoreInterval(detail.score.scoreInterval)} />
            <ScorePill label="证据条数" value={String(detail.evidence.length)} />
            <ScorePill label="观点条数" value={String(detail.opinions.length)} />
          </div>
          <p className={styles.summaryProse}>
            系统在本次快照中共提取到 {detail.evidence.length} 条来源材料，
            {detail.opinions.length} 组观点归因，
            {detail.graph.edges.length} 条传导假设。研究员本次评审已
            <strong> 纳入 {groupedOpinions.include.length} </strong>
            条观点、
            <strong> 排除 {groupedOpinions.exclude.length} </strong>
            条观点，其余
            <strong> {groupedOpinions.undecided.length} </strong>
            条待复核。以下结论仅基于当前快照，不对未纳入观点做隐含背书。
          </p>
        </section>

        {groupedOpinions.include.length > 0 ? (
          <section>
            <h2 className={styles.h2}>二、纳入本次结论的观点</h2>
            <ol className={styles.opinionList}>
              {groupedOpinions.include.map((item) => (
                <OpinionRow
                  key={item.id}
                  item={item}
                  note={getState(item.id).note}
                />
              ))}
            </ol>
          </section>
        ) : null}

        {groupedOpinions.undecided.length > 0 ? (
          <section>
            <h2 className={styles.h2}>三、系统识别但研究员尚未定夺</h2>
            <ol className={styles.opinionList}>
              {groupedOpinions.undecided.map((item) => (
                <OpinionRow
                  key={item.id}
                  item={item}
                  note={getState(item.id).note}
                  muted
                />
              ))}
            </ol>
          </section>
        ) : null}

        {groupedOpinions.exclude.length > 0 ? (
          <section>
            <h2 className={styles.h2}>四、已排除的观点（附排除理由）</h2>
            <ol className={styles.opinionList}>
              {groupedOpinions.exclude.map((item) => (
                <OpinionRow
                  key={item.id}
                  item={item}
                  note={getState(item.id).note}
                  strike
                />
              ))}
            </ol>
          </section>
        ) : null}

        {detail.graph.edges.length > 0 ? (
          <section>
            <h2 className={styles.h2}>五、传导假设</h2>
            {detail.availability.transmission === "available" ? (
              <div className={styles.chartFrame}>
                <TransmissionGraph
                  graph={detail.graph}
                  status={detail.availability.transmission}
                  eventId={detail.id}
                />
              </div>
            ) : null}
            <p className={styles.chartFrameCaption}>
              下表为传导假设的结构化明细，与上图一一对应。
            </p>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>源</th>
                  <th>→</th>
                  <th>目标</th>
                  <th>机制</th>
                  <th>置信度</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {detail.graph.edges.map((edge) => {
                  const src = detail.graph.nodes.find((n) => n.id === edge.source);
                  const tgt = detail.graph.nodes.find((n) => n.id === edge.target);
                  return (
                    <tr key={edge.id}>
                      <td>{src?.label ?? edge.source}</td>
                      <td aria-hidden="true">→</td>
                      <td>{tgt?.label ?? edge.target}</td>
                      <td>{edge.mechanism}</td>
                      <td data-numeric>{formatScore(edge.confidence)}</td>
                      <td>
                        <span
                          className={styles.pill}
                          data-status={edge.status.toLowerCase()}
                        >
                          {edge.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ) : null}

        {detail.impactMatrix.length > 0 ? (
          <section>
            <h2 className={styles.h2}>六、影响热力矩阵</h2>
            <div className={styles.chartFrame}>
              <ImpactMatrix
                rows={detail.impactMatrix}
                status={detail.availability.impact}
              />
            </div>
          </section>
        ) : null}

        <section>
          <h2 className={styles.h2}>七、证据附录</h2>
          {(Object.entries(groupedEvidence) as [string, typeof detail.evidence][]).map(
            ([tier, items]) =>
              items.length > 0 ? (
                <div key={tier} className={styles.evidenceGroup}>
                  <h3 className={styles.h3}>
                    {SOURCE_TIER_LABELS[tier] ?? tier}
                    <span className={styles.evidenceCount} data-numeric>
                      {items.length} 条
                    </span>
                  </h3>
                  <ol className={styles.evidenceList}>
                    {items.map((e) => (
                      <li key={e.id} className={styles.evidenceItem}>
                        <p className={styles.evidenceHead}>
                          <span className={styles.evidenceSource}>{e.source}</span>
                          <span className={styles.metaSep}>·</span>
                          <span data-numeric>{formatDateTime(e.publishedAt)}</span>
                        </p>
                        <p className={styles.evidenceTitle}>{e.title}</p>
                        {e.body ? (
                          <p className={styles.evidenceBody}>{e.body}</p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null,
          )}
        </section>

        <footer className={styles.paperFoot}>
          <p>
            本报告基于 RiskTrace 事件工作台在 {formatDateTime(now.toISOString())} 的实时快照生成。
            观点纳入/排除/研判备注为研究员本地标注，未回写后端。
          </p>
          <p>
            <span data-numeric>{reportId}</span>
            <span className={styles.metaSep}>·</span>
            事件 ID <span data-numeric>{detail.id}</span>
          </p>
        </footer>
      </article>
    </div>,
    document.body,
  );
}

function ScorePill({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.scorePill}>
      <span className={styles.scorePillLabel}>{label}</span>
      <span className={styles.scorePillValue} data-numeric>
        {value}
      </span>
    </div>
  );
}

function OpinionRow({
  item,
  note,
  muted,
  strike,
}: {
  item: OpinionAttribution;
  note: string;
  muted?: boolean;
  strike?: boolean;
}) {
  const classes = [styles.opinionItem];
  if (muted) classes.push(styles.opinionItemMuted);
  if (strike) classes.push(styles.opinionItemStrike);
  return (
    <li className={classes.join(" ")}>
      <p className={styles.opinionReason}>{item.reason}</p>
      <p className={styles.opinionExcerpt}>「{item.excerpt}」</p>
      <p className={styles.opinionMeta}>
        <span className={styles.opinionMetaTag}>
          {localize(item.stance, STANCE_LABELS)}
        </span>
        <span className={styles.opinionMetaTag}>
          {localize(item.claimType, CLAIM_TYPE_LABELS)}
        </span>
        <span>{item.source}</span>
        <span className={styles.metaSep}>·</span>
        <span data-numeric>{formatDateTime(item.publishedAt)}</span>
        <span className={styles.metaSep}>·</span>
        <span>置信度 <strong data-numeric>{formatScore(item.confidence, 0)}</strong></span>
      </p>
      {note ? (
        <p className={styles.opinionNote}>
          <span className={styles.opinionNoteLabel}>研判</span>
          {note}
        </p>
      ) : null}
    </li>
  );
}
