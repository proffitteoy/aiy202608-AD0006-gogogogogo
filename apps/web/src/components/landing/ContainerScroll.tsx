"use client";

import { useEffect, useState, type ReactNode } from "react";

import { useScrollProgress } from "@/hooks/use-scroll-progress";

import styles from "./ContainerScroll.module.css";

type Props = {
  titleComponent: ReactNode;
  children: ReactNode;
};

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * 卡片滚动揭示动画：header 上移、card 从 rotateX(20deg) 展平为 0deg、
 * scale 从 1.05（桌面）/ 0.7（移动）过渡到 1。零依赖，用自制 useScrollProgress。
 */
export function ContainerScroll({ titleComponent, children }: Props) {
  const [ref, progress] = useScrollProgress<HTMLDivElement>();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const rotate = lerp(20, 0, progress);
  const scaleFrom = isMobile ? 0.7 : 1.05;
  const scaleTo = isMobile ? 0.9 : 1;
  const scale = lerp(scaleFrom, scaleTo, progress);
  const translate = lerp(0, -100, progress);

  return (
    <div ref={ref} className={styles.wrap}>
      <div className={styles.inner}>
        <div
          className={styles.header}
          style={{ transform: `translateY(${translate}px)` }}
        >
          {titleComponent}
        </div>
        <div
          className={styles.card}
          style={{
            transform: `rotateX(${rotate}deg) scale(${scale})`,
          }}
        >
          <div className={styles.canvas}>{children}</div>
        </div>
      </div>
    </div>
  );
}
