import Link from "next/link";

import { ContainerScroll } from "@/components/landing/ContainerScroll";
import { WorkbenchPreview } from "@/components/landing/WorkbenchPreview";

import styles from "./page.module.css";

const DEMO_EVENT_ID = "4a897de9-f136-4e25-bc87-06c2920473c8";

const FEATURES = [
  {
    n: "01",
    title: "事件识别",
    tag: "确定性聚合",
    text: "把碎片化的官方文件、专业媒体与社交讨论，聚合成可复算的事件簇——每个簇都有唯一 ID、时间线和证据集。",
  },
  {
    n: "02",
    title: "观点归因",
    tag: "LLM 候选 + 人工确认",
    text: "LLM 提取立场、情绪与关键词，研究员一键纳入、排除或标注。分歧观点会同时保留，不合并成单一结论。",
  },
  {
    n: "03",
    title: "传导假设",
    tag: "候选而非因果",
    text: "自动生成 主体 → 板块 → 行业 的影响候选，每条边都可点开支撑证据。系统只提供假设，不宣称因果关系。",
  },
  {
    n: "04",
    title: "研判报告",
    tag: "冻结与追溯",
    text: "冻结事件当下的评分、观点与证据快照，研究员的标注写进研报正文，可打印、可导出 PDF、可版本对比。",
  },
];

const STATS = [
  { n: "5", u: "条社交讨论", meta: "跨平台聚合" },
  { n: "20", u: "篇原文", meta: "官方 · 媒体 · 社交" },
  { n: "4", u: "类主体", meta: "监管 · 上市公司 · 板块 · 行业" },
  { n: "R3+R4", u: "评分校准", meta: "确定性 + 后验修正" },
];

export default function LandingPage() {
  return (
    <main className={styles.main}>
      <ContainerScroll
        titleComponent={
          <div className={styles.hero}>
            <p className={styles.eyebrow}>金融事件 · 社交情绪 · 市场传导</p>
            <h1 className={styles.heroTitle}>
              把突发事件后的
              <br />
              海量信息，压缩成可核对的结论
            </h1>
            <p className={styles.heroLead}>
              事件识别、观点归因、传导假设、证据下钻—— 一条链路留住每个结论的出处。
            </p>
          </div>
        }
      >
        <WorkbenchPreview />
      </ContainerScroll>

      <section className={styles.features}>
        <div className={styles.featuresInner}>
          <header className={styles.sectionHead}>
            <p className={styles.sectionEyebrow}>
              <span className={styles.sectionEyebrowMark} aria-hidden="true">
                ▎
              </span>
              四层可核对能力
            </p>
            <h2 className={styles.sectionTitle}>
              研究员看得见推导过程，也看得见证据
            </h2>
            <p className={styles.sectionLead}>
              系统只做确定性可复算的部分——事件识别、评分、观点候选、传导候选、证据链。
              判断和结论由研究员做，人和机器的边界从头到尾清晰。
            </p>
          </header>

          <div className={styles.featureGrid}>
            {FEATURES.map((f) => (
              <article key={f.title} className={styles.featureCard}>
                <div className={styles.featureHead}>
                  <span className={styles.featureN} data-numeric>
                    {f.n}
                  </span>
                  <span className={styles.featureTag}>{f.tag}</span>
                </div>
                <h3 className={styles.featureTitle}>{f.title}</h3>
                <p className={styles.featureText}>{f.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.cta}>
        <div className={styles.ctaInner}>
          <header className={styles.ctaHead}>
            <p className={styles.ctaEyebrow}>Live Demo · 真实事件</p>
            <h2 className={styles.ctaTitle}>
              看一个真实事件是怎么被追溯的
            </h2>
            <p className={styles.ctaLead}>
              以 2026 年 7 月 22 日
              <em className={styles.ctaEm}>能源转型四关键词引爆 A 股涨停潮</em>
              为例——真实社交讨论、真实原文、真实评分与传导候选，全部可点、可下钻、可导出。
            </p>
          </header>

          <div className={styles.stats} role="list">
            {STATS.map((s) => (
              <div key={s.u} className={styles.stat} role="listitem">
                <span className={styles.statN} data-numeric>
                  {s.n}
                </span>
                <span className={styles.statU}>{s.u}</span>
                <span className={styles.statMeta}>{s.meta}</span>
              </div>
            ))}
          </div>

          <div className={styles.ctaActions}>
            <Link href={`/event/${DEMO_EVENT_ID}`} className={styles.ctaPrimary}>
              <span>打开 Demo 事件</span>
              <span className={styles.ctaArrow} aria-hidden="true">
                →
              </span>
            </Link>
            <Link href="/pulse" className={styles.ctaSecondary}>
              查看事件流
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
