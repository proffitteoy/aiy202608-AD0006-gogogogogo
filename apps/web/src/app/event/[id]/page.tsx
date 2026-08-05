import { notFound } from "next/navigation";

import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { EvidenceProvider } from "@/components/evidence/EvidenceContext";
import { DemoRevealProvider } from "@/components/workbench/DemoRevealContext";
import { WorkbenchBody } from "@/components/workbench/WorkbenchBody";
import { Header } from "@/components/ui/Header";
import { loadEventDetail } from "@/lib/api/loaders";

import styles from "./page.module.css";

type Params = { id: string };

export default async function EventWorkbenchPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const loaded = await loadEventDetail(id);

  if (loaded.status === "not_found") {
    notFound();
  }

  if (loaded.status === "unavailable") {
    return (
      <div data-theme="dark" className="themeShell">
        <Header />
        <main className={styles.errorPage}>
          <p className="eyebrow">EVENT WORKSPACE</p>
          <h1>事件工作台暂不可用</h1>
          <p>{loaded.reason}，页面未回退到本地样例。</p>
        </main>
      </div>
    );
  }

  const detail = loaded.data;

  return (
    <div data-theme="dark" className="themeShell">
      <EvidenceProvider evidence={detail.evidence}>
        <DemoRevealProvider>
          <div className={styles.layout}>
            <WorkbenchBody detail={detail} warnings={loaded.warnings} />
          </div>

          <EvidenceDrawer />
        </DemoRevealProvider>
      </EvidenceProvider>
    </div>
  );
}
