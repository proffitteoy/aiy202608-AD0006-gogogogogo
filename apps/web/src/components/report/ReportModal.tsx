"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";

import { Sparkline } from "@/components/overview/Sparkline";
import { formatDateTime, formatNumber, formatSentiment, formatTime } from "@/lib/format";
import type { EventDetail } from "@/lib/types";

import styles from "./ReportModal.module.css";

type Props = {
  detail: EventDetail;
  onClose: () => void;
};

const riskLabel = { high: "高", mid: "中", low: "低" } as const;

export function ReportModal({ detail, onClose }: Props) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  if (typeof document === "undefined") return null;

  const peakHeat = Math.max(...detail.timeline.map((p) => p.heat));
  const avgSentiment =
    detail.timeline.reduce((s, p) => s + p.sentiment, 0) / detail.timeline.length;
  const confirmedEdges = detail.graph.edges.filter((e) => e.confirmed).length;
  const totalEvidence = detail.evidence.length;
  const authoritativeEvidence = detail.evidence.filter(
    (e) => e.sourceTier === "authoritative",
  ).length;

  const heatSeries = detail.timeline.map((p) => p.heat);

  return createPortal(
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="报告预览">
      <header className={styles.head}>
        <div className={styles.headLeft}>
          <p className="eyebrow">报告预览</p>
          <p className={styles.headMeta} data-numeric>
            A4 · v{detail.version} · {formatDateTime(detail.freshness?.updatedAt ?? detail.publishedAt)}
          </p>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={() => window.print()}
          >
            打印
          </button>
          <button
            type="button"
            className={styles.exportBtn}
            onClick={() => window.print()}
            title="调用系统打印对话框，选择「另存为 PDF」"
          >
            导出 PDF
          </button>
          <button type="button" className={styles.close} onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>
      </header>

      <div className={styles.scroll}>
        <article className={styles.paper}>
          {/* --- 顶部色带（真报告都有的标识线，铺满屏幕） --- */}
          <div className={styles.topStrip} aria-hidden="true" />

          <div className={styles.paperInner}>
          {/* --- 品牌行 --- */}
          <div className={styles.brandBar}>
            <div className={styles.brandRow}>
              <span className={styles.brandMark} aria-hidden="true">◆</span>
              <span className={styles.brandName}>RiskTrace</span>
              <span className={styles.divider} aria-hidden="true">/</span>
              <span className={styles.brandType}>事件复盘报告</span>
            </div>
            <span className={styles.docId} data-numeric>
              DOC · {detail.id.toUpperCase()} · v{detail.version}
            </span>
          </div>

          {/* --- 报告主标题 --- */}
          <h1 className={styles.title}>{detail.title}</h1>

          {/* --- 事件元信息 --- */}
          <div className={styles.metaRow}>
            <span data-numeric>{formatDateTime(detail.publishedAt)}</span>
            <span className={styles.dot} aria-hidden="true">·</span>
            <span>
              风险等级{" "}
              <strong className={styles[`risk-${detail.risk}`]}>
                {riskLabel[detail.risk]}
              </strong>
            </span>
            <span className={styles.dot} aria-hidden="true">·</span>
            <span data-numeric>
              {totalEvidence} 篇原文 / {authoritativeEvidence} 权威
            </span>
            <span className={styles.dot} aria-hidden="true">·</span>
            <span data-numeric>
              已确认边 {confirmedEdges}/{detail.graph.edges.length}
            </span>
          </div>

          <hr className={styles.rule} />

          {/* --- 双栏正文 --- */}
          <div className={styles.body}>
            {/* 左栏：正文 */}
            <div className={styles.main}>
              <section className={styles.section}>
                <h2 className={styles.h2}>摘要</h2>
                <p className={styles.p}>
                  本事件于 {formatDateTime(detail.publishedAt)} 首次被 {detail.evidence[0]?.source ?? "权威源"} 披露，随后热度在 40 分钟内攀升至 {formatNumber(peakHeat)}，情绪均值 {formatSentiment(avgSentiment)}。共 {totalEvidence} 篇原文覆盖，其中 {authoritativeEvidence} 篇来自权威媒体。
                </p>
                <p className={styles.p}>
                  LLM 抽取到 {detail.clusters.length} 个观点簇，规则引擎识别出 {detail.graph.edges.length} 条候选传导路径，其中 {confirmedEdges} 条已由研究员确认。核心传导链指向控股股东关联的境外主体资金流向，与季报数据反差形成印证。
                </p>
              </section>

              <section className={styles.section}>
                <h2 className={styles.h2}>核心观点</h2>
                <ol className={styles.clusterList}>
                  {detail.clusters.map((c) => (
                    <li key={c.id} className={styles.clusterItem}>
                      <div className={styles.clusterHead}>
                        <span className={styles.clusterTitle}>{c.label}</span>
                        <span className={styles.clusterSupport} data-numeric>
                          支持度 {Math.round(c.support * 100)}%
                        </span>
                      </div>
                      <p className={styles.clusterExcerpt}>{c.representativeExcerpt}</p>
                      <p className={styles.clusterSource}>
                        @{c.representativeSource} · {formatTime(c.representativeAt)}
                        {c.authoritative && <span className={styles.authTag}>权威</span>}
                      </p>
                    </li>
                  ))}
                </ol>
              </section>

              <section className={styles.section}>
                <h2 className={styles.h2}>证据列表</h2>
                <ol className={styles.evList}>
                  {detail.evidence.map((item, i) => (
                    <li key={item.id} className={styles.evItem}>
                      <span className={styles.evNum} data-numeric>
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div className={styles.evBody}>
                        <p className={styles.evHead}>
                          <span className={styles.evSource}>{item.source}</span>
                          <span className={styles.evTime} data-numeric>
                            {formatDateTime(item.publishedAt)}
                          </span>
                        </p>
                        <p className={styles.evTitle}>{item.title}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>

              <section className={styles.section}>
                <h2 className={styles.h2}>数据缺失说明</h2>
                <p className={styles.pMuted}>
                  本报告未包含「境外舆情」维度：对应数据源当前不可用。若后续采集恢复，报告将以新版本发布，本版本保留为快照。
                </p>
              </section>
            </div>

            {/* 右栏：sidebar */}
            <aside className={styles.side}>
              <div className={styles.sideBlock}>
                <p className="eyebrow">关键指标</p>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>热度峰值</span>
                  <span className={styles.statValue} data-numeric>
                    {formatNumber(peakHeat)}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>平均情绪</span>
                  <span
                    className={`${styles.statValue} ${
                      avgSentiment < 0 ? styles.negative : styles.positive
                    }`}
                    data-numeric
                  >
                    {formatSentiment(avgSentiment)}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>证据数</span>
                  <span className={styles.statValue} data-numeric>
                    {totalEvidence}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>已确认边</span>
                  <span className={styles.statValue} data-numeric>
                    {confirmedEdges}/{detail.graph.edges.length}
                  </span>
                </div>
              </div>

              <div className={styles.sideBlock}>
                <p className="eyebrow">热度曲线</p>
                <Sparkline
                  data={heatSeries}
                  width={240}
                  height={64}
                  strokeColor="var(--viz-1)"
                />
                <p className={styles.miniHint} data-numeric>
                  过去 {detail.timeline.length} 个采样点
                </p>
              </div>

              <div className={styles.sideBlock}>
                <p className="eyebrow">受影响维度</p>
                <ul className={styles.impactList}>
                  {detail.impact.rows.slice(0, 4).map((row, r) => {
                    const value =
                      detail.impact.cells[r]?.reduce((s, v) => s + Math.abs(v), 0) /
                      detail.impact.cols.length;
                    return (
                      <li key={row} className={styles.impactRow}>
                        <span className={styles.impactLabel}>{row}</span>
                        <span className={styles.impactBar}>
                          <span
                            className={styles.impactFill}
                            style={{ width: `${Math.min(100, value * 100)}%` }}
                          />
                        </span>
                        <span className={styles.impactVal} data-numeric>
                          {value.toFixed(2)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>

              <div className={styles.sideBlock}>
                <p className="eyebrow">版本信息</p>
                <p className={styles.versionText}>
                  当前版本 <strong data-numeric>v{detail.version}</strong>
                </p>
                <p className={styles.versionText}>
                  更新于{" "}
                  <span data-numeric>
                    {formatDateTime(detail.freshness?.updatedAt ?? detail.publishedAt)}
                  </span>
                </p>
                <p className={styles.versionText}>
                  本报告基于当前工作台状态生成，所有结论可通过证据列表回溯。
                </p>
              </div>
            </aside>
          </div>

          {/* --- 页脚 --- */}
          <footer className={styles.pageFoot}>
            <span>RiskTrace · 事件复盘报告</span>
            <span data-numeric>{detail.id.toUpperCase()} · v{detail.version}</span>
            <span data-numeric>Page 1 / 1</span>
          </footer>
          </div>
        </article>
      </div>
    </div>,
    document.body,
  );
}
