"use client";

import { useCallback, useEffect, useState } from "react";

type Dependency = {
  status: "up" | "down";
  latency_ms: number;
  detail?: string | null;
};

type PlatformStatus = {
  status: "loading" | "ready" | "degraded" | "unavailable";
  service?: string;
  version?: string;
  timestamp?: string;
  dependencies?: Record<string, Dependency> | null;
  detail?: string;
};

const dependencyNames: Record<string, string> = {
  database: "PostgreSQL",
  redis: "Redis",
  object_storage: "对象存储",
};

export default function Home() {
  const [platform, setPlatform] = useState<PlatformStatus>({ status: "loading" });

  const refresh = useCallback(async () => {
    setPlatform({ status: "loading" });
    try {
      const response = await fetch("/api/platform-status", { cache: "no-store" });
      const data = (await response.json()) as PlatformStatus;
      setPlatform(data);
    } catch {
      setPlatform({
        status: "unavailable",
        detail: "状态接口不可访问。请检查 Web 服务日志。",
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const statusLabel = {
    loading: "检查中",
    ready: "基础设施就绪",
    degraded: "依赖降级",
    unavailable: "后端不可用",
  }[platform.status];

  return (
    <main>
      <header className="site-header">
        <div className="brand">
          <img src="/mark.svg" alt="" width={38} height={38} />
          <span>RiskTrace</span>
        </div>
        <span className="phase">MVP · 工程基线</span>
      </header>

      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">RESEARCH INFRASTRUCTURE</p>
        <h1 id="page-title">先让每条结论有出处，<br />再讨论它意味着什么。</h1>
        <p className="lede">
          金融事件、社交情绪与市场传导的可追溯研究工作台。当前页面只呈现真实运行状态，
          尚未导入的事件不会用演示数据代替。
        </p>
      </section>

      <section className="status-panel" aria-live="polite">
        <div className="status-heading">
          <div>
            <p className="section-label">SYSTEM STATUS</p>
            <h2>运行基础</h2>
          </div>
          <div className={`status-badge status-${platform.status}`}>
            <span aria-hidden="true" />
            {statusLabel}
          </div>
        </div>

        {platform.dependencies ? (
          <div className="dependency-grid">
            {Object.entries(platform.dependencies).map(([name, dependency]) => (
              <article className="dependency" key={name}>
                <div className="dependency-title">
                  <h3>{dependencyNames[name] ?? name}</h3>
                  <span className={`dependency-state state-${dependency.status}`}>
                    {dependency.status === "up" ? "正常" : "不可用"}
                  </span>
                </div>
                <p>{dependency.latency_ms.toFixed(1)} ms</p>
                {dependency.detail ? <small>诊断：{dependency.detail}</small> : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <p>{platform.detail ?? "正在读取后端和基础设施状态……"}</p>
          </div>
        )}

        <div className="status-footer">
          <span>
            {platform.timestamp
              ? `检查时间 ${new Intl.DateTimeFormat("zh-CN", {
                  dateStyle: "medium",
                  timeStyle: "medium",
                }).format(new Date(platform.timestamp))}`
              : "尚无检查时间"}
          </span>
          <button type="button" onClick={() => void refresh()} disabled={platform.status === "loading"}>
            重新检查
          </button>
        </div>
      </section>

      <section className="boundary-grid" aria-label="系统边界">
        <article>
          <span>01</span>
          <h2>规则计算</h2>
          <p>状态、阈值和风险指标由可复算、可版本化的程序负责。</p>
        </article>
        <article>
          <span>02</span>
          <h2>模型候选</h2>
          <p>LLM 只提出结构化语义候选，不能写入权威结论或风险分数。</p>
        </article>
        <article>
          <span>03</span>
          <h2>人工确认</h2>
          <p>传导关系、重大结论和外发内容最终由研究员审核并留痕。</p>
        </article>
      </section>
    </main>
  );
}
