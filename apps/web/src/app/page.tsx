import { EventCard } from "@/components/overview/EventCard";
import { PulseTiles } from "@/components/overview/PulseTiles";
import { DegradedBanner } from "@/components/ui/DegradedBanner";
import { Header } from "@/components/ui/Header";
import { derivePulse, loadEventList } from "@/lib/api/loaders";

import styles from "./page.module.css";

export default async function OverviewPage() {
  const result = await loadEventList();
  const events = result.data;
  const pulse = derivePulse(events);

  return (
    <>
      <Header
        activeEventCount={pulse.activeEvents}
        scoredEventCount={pulse.scoredEvents}
      />
      {result.status === "degraded" ? (
        <DegradedBanner
          message="事件数据暂不可用"
          hint={`${result.reason}，未使用本地样例替代`}
        />
      ) : null}
      <main className={styles.main}>
        <section className={styles.hero}>
          <p className="eyebrow">今日 · Risk Pulse</p>
          <h1 className={styles.title}>先让每条结论有出处，再讨论它意味着什么。</h1>
          <p className={styles.dataNote} data-source={result.status}>
            数据源：RiskTrace API · 固定 Demo 研究上下文
          </p>
        </section>

        <PulseTiles pulse={pulse} />

        <section aria-label="事件流" className={styles.stream}>
          <header className={styles.streamHead}>
            <p className="eyebrow">事件流</p>
            <p className={styles.streamHint}>按首次发布时间倒序</p>
          </header>

          {events.length > 0 ? (
            <div className={styles.list}>
              {events.map((event, index) => (
                <div
                  key={event.id}
                  className={styles.item}
                  style={{ animationDelay: `${index * 60}ms` }}
                >
                  <EventCard event={event} />
                </div>
              ))}
            </div>
          ) : (
            <div className={styles.empty} role="status">
              <strong>暂无可展示事件</strong>
              <span>导入完成后，事件会从后端查询结果中出现。</span>
            </div>
          )}
        </section>
      </main>
    </>
  );
}
