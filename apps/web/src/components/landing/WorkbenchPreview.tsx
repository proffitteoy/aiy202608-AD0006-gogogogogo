import styles from "./WorkbenchPreview.module.css";

/**
 * 落地页专用的工作台预览 mockup——静态、纯 CSS + inline SVG。
 * 与真工作台数据无关，只为视觉展示。
 */
export function WorkbenchPreview() {
  return (
    <div className={styles.frame}>
      <div className={styles.chrome}>
        <span className={styles.dot} data-tone="r" />
        <span className={styles.dot} data-tone="y" />
        <span className={styles.dot} data-tone="g" />
        <span className={styles.chromePath}>risktrace / 事件工作台 · 光伏电价新政</span>
      </div>

      <div className={styles.grid}>
        {/* 时间线 */}
        <section className={styles.panel}>
          <header className={styles.panelHead}>
            <span className={styles.panelIcon}>◔</span>
            <span className={styles.panelTitle}>事件时间线</span>
            <span className={styles.panelMeta}>6 个时间点</span>
          </header>
          <div className={styles.panelBody}>
            <svg viewBox="0 0 320 120" className={styles.timelineSvg} aria-hidden="true">
              <defs>
                <linearGradient id="tlFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3e6bd6" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#3e6bd6" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path
                d="M 10 90 L 60 70 L 110 40 L 160 30 L 210 55 L 260 65 L 310 45 L 310 110 L 10 110 Z"
                fill="url(#tlFill)"
              />
              <path
                d="M 10 90 L 60 70 L 110 40 L 160 30 L 210 55 L 260 65 L 310 45"
                stroke="#5a86e6"
                strokeWidth="2"
                fill="none"
              />
              {[
                [10, 90],
                [60, 70],
                [110, 40],
                [160, 30],
                [210, 55],
                [260, 65],
                [310, 45],
              ].map(([x, y], i) => (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="3.5"
                  fill="#1a1d24"
                  stroke="#5a86e6"
                  strokeWidth="1.5"
                />
              ))}
            </svg>
            <div className={styles.axisRow}>
              <span>03-14 08:00</span>
              <span>15:30</span>
              <span>03-15 18:00</span>
            </div>
          </div>
        </section>

        {/* 观点归因 */}
        <section className={styles.panel}>
          <header className={styles.panelHead}>
            <span className={styles.panelIcon}>◈</span>
            <span className={styles.panelTitle}>观点归因</span>
            <span className={styles.panelMeta}>5 条</span>
          </header>
          <div className={styles.panelBody}>
            <ul className={styles.opinionList}>
              {[
                { tag: "看多", tone: "up", text: "电网设备与储能一起拉升不是偶然" },
                { tag: "看多", tone: "up", text: "先看电网设备，再看储能兑现" },
                { tag: "看空", tone: "down", text: "涨停潮之后要防止高位追涨" },
                { tag: "观望", tone: "neutral", text: "从普涨转成细分龙头分化" },
              ].map((o, i) => (
                <li key={i} className={styles.opinion}>
                  <span className={styles.opinionTag} data-tone={o.tone}>
                    {o.tag}
                  </span>
                  <span className={styles.opinionText}>{o.text}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* 传导假设 */}
        <section className={styles.panel}>
          <header className={styles.panelHead}>
            <span className={styles.panelIcon}>⇋</span>
            <span className={styles.panelTitle}>传导假设</span>
            <span className={styles.panelMeta}>4 节点 / 3 边</span>
          </header>
          <div className={styles.panelBody}>
            <svg viewBox="0 0 320 160" className={styles.graphSvg} aria-hidden="true">
              <defs>
                <marker
                  id="arrowW"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#5a86e6" />
                </marker>
              </defs>
              <line x1="70" y1="45" x2="160" y2="80" stroke="#5a86e6" strokeWidth="1.5" markerEnd="url(#arrowW)" />
              <line x1="70" y1="115" x2="160" y2="80" stroke="#5a86e6" strokeWidth="1.5" markerEnd="url(#arrowW)" />
              <line x1="160" y1="80" x2="255" y2="80" stroke="#e88b52" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrowW)" />

              <g>
                <rect x="10" y="30" width="120" height="30" rx="4" fill="#232630" stroke="#3d434f" />
                <text x="70" y="49" textAnchor="middle" fill="#e0e2e6" fontSize="11">国家能源局</text>
              </g>
              <g>
                <rect x="10" y="100" width="120" height="30" rx="4" fill="#232630" stroke="#3d434f" />
                <text x="70" y="119" textAnchor="middle" fill="#e0e2e6" fontSize="11">光伏电价新政</text>
              </g>
              <g>
                <rect x="140" y="65" width="80" height="30" rx="4" fill="#232630" stroke="#5a86e6" strokeWidth="1.5" />
                <text x="180" y="84" textAnchor="middle" fill="#a8c4f2" fontSize="11">光伏板块</text>
              </g>
              <g>
                <rect x="230" y="65" width="80" height="30" rx="4" fill="#232630" stroke="#e88b52" strokeWidth="1.5" strokeDasharray="3 2" />
                <text x="270" y="84" textAnchor="middle" fill="#f0c4a0" fontSize="11">储能行业</text>
              </g>
            </svg>
          </div>
        </section>

        {/* 影响矩阵 */}
        <section className={styles.panel}>
          <header className={styles.panelHead}>
            <span className={styles.panelIcon}>▦</span>
            <span className={styles.panelTitle}>影响矩阵</span>
            <span className={styles.panelMeta}>4 主体 × 3 维</span>
          </header>
          <div className={styles.panelBody}>
            <table className={styles.matrix}>
              <thead>
                <tr>
                  <th />
                  <th>价格</th>
                  <th>流动性</th>
                  <th>舆情</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["隆基绿能", -0.85, -0.42, -0.61],
                  ["通威股份", -0.72, -0.35, -0.48],
                  ["阳光电源", 0.32, 0.18, 0.55],
                  ["宁德时代", 0.78, 0.42, 0.66],
                ].map(([name, ...vals]) => (
                  <tr key={name as string}>
                    <td className={styles.matrixLabel}>{name}</td>
                    {(vals as number[]).map((v, i) => (
                      <td key={i} className={styles.matrixCell}>
                        <span
                          className={styles.matrixValue}
                          data-tone={v > 0 ? "up" : "down"}
                          data-extreme={Math.abs(v) >= 0.8 || undefined}
                        >
                          {v > 0 ? "+" : ""}
                          {v.toFixed(2)}
                        </span>
                        <span
                          className={styles.matrixBar}
                          data-tone={v > 0 ? "up" : "down"}
                          style={{ width: `${Math.min(Math.abs(v) * 100, 100)}%` }}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
