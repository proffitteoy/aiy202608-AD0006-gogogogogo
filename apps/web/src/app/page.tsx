import { EventCard } from "@/components/overview/EventCard";
import { PulseTiles } from "@/components/overview/PulseTiles";
import { Header } from "@/components/ui/Header";
import { loadEventList, loadPulse } from "@/lib/api/loaders";

import styles from "./page.module.css";

export default async function OverviewPage() {
  const [pulseResult, eventsResult] = await Promise.all([
    loadPulse(),
    loadEventList(),
  ]);
  const pulse = pulseResult.data;
  const events = eventsResult.data;
  const usingMock =
    pulseResult.source === "mock" || eventsResult.source === "mock";

  return (
    <>
      <Header
        activeEventCount={pulse.activeEvents}
        highRiskCount={pulse.highRiskEvents}
      />
      <main className={styles.main}>
        <section className={styles.hero}>
          <p className="eyebrow">今日 · Risk Pulse</p>
          <h1 className={styles.title}>先让每条结论有出处，再讨论它意味着什么。</h1>
          {usingMock ? (
            <p className={styles.dataNote} data-source="mock">
              数据源：本地样例 · 后端未连通或返回空
            </p>
          ) : (
            <p className={styles.dataNote} data-source="backend">
              数据源：RiskTrace API
            </p>
          )}
        </section>

        <PulseTiles pulse={pulse} />

        <section aria-label="事件流" className={styles.stream}>
          <header className={styles.streamHead}>
            <p className="eyebrow">事件流</p>
            <p className={styles.streamHint}>
              按热度 × 净情绪 × 来源质量排序 · 每 30 秒刷新
            </p>
          </header>

          <div className={styles.list}>
            {events.map((event, i) => (
              <div
                key={event.id}
                className={styles.item}
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <EventCard event={event} />
              </div>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
