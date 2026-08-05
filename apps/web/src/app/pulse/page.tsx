import { OverviewStream } from "@/components/overview/OverviewStream";
import { PulseTiles } from "@/components/overview/PulseTiles";
import { Header } from "@/components/ui/Header";
import { derivePulse, loadEventList } from "@/lib/api/loaders";

import styles from "./page.module.css";

export default async function PulsePage() {
  const result = await loadEventList();
  const events = result.data;
  const pulse = derivePulse(events);

  return (
    <div data-theme="dark" className="themeShell">
      <Header
        activeEventCount={pulse.activeEvents}
        scoredEventCount={pulse.scoredEvents}
      />
      <main className={styles.main}>
        <section className={styles.pulseSection} aria-label="平台脉搏">
          <PulseTiles pulse={pulse} />
        </section>

        <section className={styles.streamSection} aria-label="事件流">
          <OverviewStream events={events} />
        </section>
      </main>
    </div>
  );
}
