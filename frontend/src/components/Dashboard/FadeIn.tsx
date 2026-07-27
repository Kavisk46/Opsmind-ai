"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

interface FadeInProps {
  children: ReactNode;
  delay?: number;
  className?: string;
}

const variants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
};

// Shared, deliberately subtle entrance animation used across every
// Dashboard section — a short fade plus a slight rise, staggered via
// `delay` for grids of cards. Skips the transform entirely under
// prefers-reduced-motion, the same accessibility contract the rest of
// this app's CSS animations already follow (see lib/utils.ts's
// POPOVER_PANEL_CLASS motion-reduce:animate-none).
export function FadeIn({ children, delay = 0, className }: FadeInProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={shouldReduceMotion ? false : "hidden"}
      animate="visible"
      variants={variants}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
