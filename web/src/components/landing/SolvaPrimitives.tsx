import { Fragment, useState, useEffect, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

/* ============================================================
   SOLVA EDITORIAL PRIMITIVES — CITRA (SourceLogic)
   Exact 1:1 Visual, Scroll-Linked & Interactive Building Blocks
   ============================================================ */

export type Lang = 'en' | 'vi';

/* ------------------------------------------------------------
   SHARED RAF SCROLL SUBSCRIBER (120fps GPU-composited updates)
   ------------------------------------------------------------ */
type ScrollCallback = () => void;
const scrollSubscribers = new Set<ScrollCallback>();
let rafId: number | null = null;
let listenersAttached = false;

function flushScrollSubscribers() {
  rafId = null;
  scrollSubscribers.forEach((cb) => cb());
}

function handleGlobalScrollOrResize() {
  if (rafId === null && typeof window !== 'undefined') {
    rafId = window.requestAnimationFrame(flushScrollSubscribers);
  }
}

function subscribeToScroll(cb: ScrollCallback): () => void {
  scrollSubscribers.add(cb);
  if (!listenersAttached && typeof window !== 'undefined') {
    listenersAttached = true;
    window.addEventListener('scroll', handleGlobalScrollOrResize, { passive: true });
    window.addEventListener('resize', handleGlobalScrollOrResize, { passive: true });
  }
  cb();
  return () => {
    scrollSubscribers.delete(cb);
    if (scrollSubscribers.size === 0 && listenersAttached && typeof window !== 'undefined') {
      listenersAttached = false;
      window.removeEventListener('scroll', handleGlobalScrollOrResize);
      window.removeEventListener('resize', handleGlobalScrollOrResize);
    }
  };
}

/**
 * 0. Reversible Scroll-Linked Reveal Wrapper (`SolvaScrollReveal`)
 * - Scrolling down into view: smoothly transitions from faded/blurred/shifted
 *   (`opacity: 0.02`, `translate3d(0, yOffset, 0)`, `scale(scaleFrom)`, `blur(blurPx)`)
 *   to crisp full visibility (`opacity: 1`, `translate3d(0,0,0)`, `scale(1)`, `blur(0px)`).
 * - Scrolling back up (`lùi lại`): as elements move back down toward the bottom edge
 *   of the viewport, they smoothly fade, blur, and glide back down.
 */
export function SolvaScrollReveal({
  children,
  delayMs = 0,
  yOffset = 32,
  scaleFrom = 0.985,
  blurPx = 3.5,
  triggerRatio = 0.91,
  className = '',
}: {
  children: ReactNode;
  delayMs?: number;
  yOffset?: number;
  scaleFrom?: number;
  blurPx?: number;
  triggerRatio?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<'visible' | 'below' | 'above'>('visible');

  useEffect(() => {
    return subscribeToScroll(() => {
      const el = ref.current;
      if (!el || typeof window === 'undefined') return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 900;

      if (rect.top > vh * triggerRatio) {
        setPhase((prev) => (prev === 'below' ? prev : 'below'));
      } else if (rect.bottom < 48) {
        setPhase((prev) => (prev === 'above' ? prev : 'above'));
      } else {
        setPhase((prev) => (prev === 'visible' ? prev : 'visible'));
      }
    });
  }, [triggerRatio]);

  const isVisible = phase === 'visible';
  const translateY = phase === 'below' ? yOffset : phase === 'above' ? -16 : 0;
  const currentScale = isVisible ? 1 : scaleFrom;
  const currentOpacity = isVisible ? 1 : 0.02;
  const currentBlur = isVisible ? 0 : blurPx;
  const activeDelay = isVisible ? delayMs : 0;

  return (
    <div
      ref={ref}
      style={{
        opacity: currentOpacity,
        transform: `translate3d(0, ${translateY}px, 0) scale(${currentScale})`,
        filter: currentBlur > 0 ? `blur(${currentBlur}px)` : 'none',
        transitionProperty: 'opacity, transform, filter',
        transitionDuration: isVisible ? '640ms' : '420ms',
        transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
        transitionDelay: `${activeDelay}ms`,
        willChange: 'transform, opacity, filter',
      }}
      className={className}
    >
      {children}
    </div>
  );
}

/**
 * 1. Eyebrow Component (`[data-framer-name="Default"]`)
 * Left indicator: 10px x 5px horizontal pill dot (#56524A)
 * Right label: Onest 15px regular (#56524A)
 */
export function SolvaEyebrow({
  children,
  centered = false,
}: {
  children: ReactNode;
  centered?: boolean;
}) {
  return (
    <SolvaScrollReveal yOffset={20} blurPx={2.5} scaleFrom={0.99}>
      <div
        className={`inline-flex items-center gap-[6px] pl-[2px] font-solva-sans ${
          centered ? 'justify-center' : ''
        }`}
      >
        <span
          className="w-[10px] h-[5px] rounded-[50px] shrink-0"
          style={{ backgroundColor: 'var(--solva-muted)' }}
        />
        <span
          className="text-[15px] font-normal leading-[19.5px]"
          style={{ color: 'var(--solva-muted)' }}
        >
          {children}
        </span>
      </div>
    </SolvaScrollReveal>
  );
}

/**
 * 2. Two-Tone Editorial Split Heading (H1 / H2) with Reversible Word-by-Word Scroll Reveal
 * Replicates Framer's word-by-word `<span style="opacity:0.001; filter:blur(3px); transform:translateY(32px)">`
 * staggered entrance and reversible scroll-up fade out.
 * Uses Sentient Light (font-weight: 300), line-height: 1.06, letter-spacing: -0.05em.
 * Clause 1: #1C1A15 (--solva-ink)
 * Clause 2: #56524A (--solva-muted)
 */
export function SolvaTwoToneHeading({
  as: Tag = 'h2',
  primary,
  secondary,
  size = 'h2',
  centered = false,
  className = '',
}: {
  as?: 'h1' | 'h2';
  primary: string;
  secondary?: string;
  size?: 'h1' | 'h2';
  centered?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLHeadingElement>(null);
  const [phase, setPhase] = useState<'visible' | 'below' | 'above'>('visible');

  useEffect(() => {
    return subscribeToScroll(() => {
      const el = ref.current;
      if (!el || typeof window === 'undefined') return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 900;

      if (rect.top > vh * 0.91) {
        setPhase((prev) => (prev === 'below' ? prev : 'below'));
      } else if (rect.bottom < 44) {
        setPhase((prev) => (prev === 'above' ? prev : 'above'));
      } else {
        setPhase((prev) => (prev === 'visible' ? prev : 'visible'));
      }
    });
  }, []);

  const sizeClass =
    size === 'h1'
      ? 'text-[40px] sm:text-[48px] xl:text-[56px] leading-[1.06] tracking-[-0.05em]'
      : 'text-[34px] sm:text-[40px] xl:text-[48px] leading-[1.06] tracking-[-0.05em]';

  const primaryWords = primary.trim().split(/\s+/);
  const secondaryWords = secondary ? secondary.trim().split(/\s+/) : [];
  const isVisible = phase === 'visible';
  const wordY = phase === 'below' ? 28 : phase === 'above' ? -14 : 0;

  const renderAnimatedWords = (words: string[], startIndex: number) =>
    words.map((word, idx) => {
      const globalIdx = startIndex + idx;
      const delay = isVisible ? Math.min(globalIdx * 28, 360) : 0;
      return (
        <Fragment key={`${word}-${idx}`}>
          <span
            className="inline-block will-change-[transform,opacity,filter]"
            style={{
              opacity: isVisible ? 1 : 0.02,
              transform: `translate3d(0, ${wordY}px, 0)`,
              filter: isVisible ? 'none' : 'blur(3.5px)',
              transitionProperty: 'opacity, transform, filter',
              transitionDuration: isVisible ? '580ms' : '360ms',
              transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
              transitionDelay: `${delay}ms`,
            }}
          >
            {word}
          </span>
          {idx < words.length - 1 ? ' ' : ''}
        </Fragment>
      );
    });

  return (
    <Tag
      ref={ref}
      className={`font-solva-serif font-light ${sizeClass} ${
        centered ? 'text-center mx-auto' : ''
      } ${className}`}
    >
      <span className="block" style={{ color: 'var(--solva-ink)' }}>
        {renderAnimatedWords(primaryWords, 0)}
      </span>
      {secondary && (
        <span className="block" style={{ color: 'var(--solva-muted)' }}>
          {renderAnimatedWords(secondaryWords, primaryWords.length)}
        </span>
      )}
    </Tag>
  );
}

/**
 * 3. Double-Text Vertical Slot-Roll Button (`Primary` & `Outline Black`)
 * Height: 44px, padding: 1px 16px 0px, border-radius: 10px, Onest 14px Medium (line-height: 21px).
 * On hover, inner 21px text window slides vertically (-21px) with cubic-bezier(0.22, 1, 0.36, 1).
 */
export function SolvaButton({
  children,
  to,
  href,
  variant = 'primary',
  fullWidth = false,
  onClick,
  className = '',
  testId,
}: {
  children: ReactNode;
  to?: string;
  href?: string;
  variant?: 'primary' | 'outline' | 'ghost';
  fullWidth?: boolean;
  onClick?: () => void;
  className?: string;
  testId?: string;
}) {
  const baseClasses = `group relative inline-flex items-center justify-center h-[44px] px-[16px] pt-[1px] rounded-[10px] font-solva-sans text-[14px] font-medium leading-[21px] transition-all duration-200 cursor-pointer select-none ${
    fullWidth ? 'w-full' : ''
  } ${className}`;

  const variantStyle =
    variant === 'primary'
      ? {
          backgroundColor: 'var(--solva-btn-bg)',
          color: 'var(--solva-btn-fg)',
        }
      : variant === 'outline'
        ? {
            backgroundColor: 'transparent',
            color: 'var(--solva-ink)',
            border: '1px solid var(--solva-border)',
          }
        : {
            backgroundColor: 'transparent',
            color: 'var(--solva-muted)',
          };

  const innerContent = (
    <span className="relative h-[21px] overflow-hidden flex flex-col items-center">
      <span className="flex flex-col transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:-translate-y-[21px]">
        <span className="h-[21px] flex items-center justify-center whitespace-nowrap gap-1.5">
          {children}
        </span>
        <span
          className="h-[21px] flex items-center justify-center whitespace-nowrap gap-1.5"
          aria-hidden="true"
        >
          {children}
        </span>
      </span>
    </span>
  );

  if (to) {
    return (
      <Link
        to={to}
        onClick={onClick}
        style={variantStyle}
        data-testid={testId}
        className={baseClasses}
      >
        {innerContent}
      </Link>
    );
  }

  if (href) {
    return (
      <a
        href={href}
        onClick={onClick}
        style={variantStyle}
        data-testid={testId}
        className={baseClasses}
      >
        {innerContent}
      </a>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      style={variantStyle}
      data-testid={testId}
      className={baseClasses}
    >
      {innerContent}
    </button>
  );
}

/**
 * 4. Painterly Frame + Film Grain Noise Overlay (opacity: 0.05, 160px tile)
 * Includes continuous scroll-linked parallax on the oil painting and floating inner widget.
 */
export function SolvaPainterlyFrame({
  paintingSrc,
  alt = '',
  children,
  className = '',
  radiusClass = 'rounded-[16px]',
}: {
  paintingSrc: string;
  alt?: string;
  children: ReactNode;
  className?: string;
  radiusClass?: string;
}) {
  const frameRef = useRef<HTMLDivElement>(null);
  const [parallaxOffset, setParallaxOffset] = useState(0);

  useEffect(() => {
    return subscribeToScroll(() => {
      const el = frameRef.current;
      if (!el || typeof window === 'undefined') return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 900;
      const centerOffset = (rect.top + rect.height / 2 - vh / 2) / (vh / 2);
      const clamped = Math.max(-1.2, Math.min(1.2, centerOffset));
      setParallaxOffset(clamped);
    });
  }, []);

  return (
    <div
      ref={frameRef}
      className={`relative overflow-hidden ${radiusClass} ${className}`}
    >
      <img
        src={paintingSrc}
        alt={alt}
        loading="eager"
        decoding="async"
        style={{
          transform: `scale(1.06) translate3d(0, ${(parallaxOffset * -10).toFixed(1)}px, 0)`,
          transition: 'transform 180ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
        className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none will-change-transform"
      />
      <div className="solva-noise-overlay" aria-hidden="true" />
      <div
        style={{
          transform: `translate3d(0, ${(parallaxOffset * 8).toFixed(1)}px, 0)`,
          transition: 'transform 220ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
        className="relative z-10 w-full h-full will-change-transform"
      >
        {children}
      </div>
    </div>
  );
}

/**
 * 5. Scroll-Triggered Sticky Stacking Card (`scale(1)` -> `scale(0.92)`)
 * Replicates Solva's Section 3 Sticky Container 1..3 stacking effect + reversible entrance.
 */
export function SolvaStickyStackCard({
  index,
  total,
  children,
}: {
  index: number;
  total: number;
  children: ReactNode;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [inView, setInView] = useState(true);

  useEffect(() => {
    return subscribeToScroll(() => {
      const el = cardRef.current;
      if (!el || typeof window === 'undefined') return;
      const rect = el.getBoundingClientRect();
      const viewportH = window.innerHeight || 900;

      // Reversible entrance when scrolling down/up
      setInView(rect.top <= viewportH * 0.92);

      if (index >= total - 1) return;
      const parent = el.parentElement;
      if (!parent) return;
      const nextSibling = parent.children[index + 1] as HTMLElement | undefined;
      if (!nextSibling) return;

      const nextRect = nextSibling.getBoundingClientRect();
      const startY = viewportH * 0.88;
      const endY = 140;
      if (nextRect.top < startY) {
        const progress = Math.max(
          0,
          Math.min(1, (startY - nextRect.top) / Math.max(1, startY - endY))
        );
        setScale(1 - progress * 0.085); // Smoothly scales from 1.0 down to 0.915
      } else {
        setScale(1);
      }
    });
  }, [index, total]);

  return (
    <div
      ref={cardRef}
      style={{
        zIndex: index + 1,
        opacity: inView ? 1 : 0.02,
        filter: inView ? 'none' : 'blur(3.5px)',
        transform: `translate3d(0, ${inView ? 0 : 32}px, 0) scale(${inView ? scale : scale * 0.97})`,
        transformOrigin: 'top center',
        backgroundColor: 'var(--solva-surface)',
        transition:
          'opacity 520ms cubic-bezier(0.22, 1, 0.36, 1), filter 480ms cubic-bezier(0.22, 1, 0.36, 1), transform 140ms ease-out',
      }}
      className="lg:sticky lg:top-[116px] w-full rounded-[16px] p-[12px] will-change-[transform,opacity,filter]"
    >
      {children}
    </div>
  );
}

/**
 * 6. Reversible Scroll-Triggered Animated Count-Up Metric (`Sentient` 40px Light)
 * Counts up when scrolled into view; resets and fades out when scrolled back up above it.
 */
export function SolvaAnimatedMetric({
  targetValue,
  suffix = '',
  prefix = '',
  decimals = 0,
  label,
}: {
  targetValue: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  label: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [displayVal, setDisplayVal] = useState<number>(targetValue);
  const [isVisible, setIsVisible] = useState(true);
  const hasAnimated = useRef(false);

  useEffect(() => {
    return subscribeToScroll(() => {
      const el = ref.current;
      if (!el || typeof window === 'undefined') return;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 900;

      if (rect.top > vh * 0.92) {
        setIsVisible(false);
        hasAnimated.current = false;
      } else if (rect.bottom >= 40) {
        setIsVisible(true);
        if (!hasAnimated.current) {
          hasAnimated.current = true;
          const duration = 950;
          const startTime = performance.now();
          const startVal = targetValue * 0.25;

          const tick = (now: number) => {
            const elapsed = now - startTime;
            const progress = Math.min(1, elapsed / duration);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = startVal + (targetValue - startVal) * eased;
            setDisplayVal(current);
            if (progress < 1 && hasAnimated.current) {
              requestAnimationFrame(tick);
            } else {
              setDisplayVal(targetValue);
            }
          };
          requestAnimationFrame(tick);
        }
      }
    });
  }, [targetValue]);

  return (
    <div
      ref={ref}
      style={{
        opacity: isVisible ? 1 : 0.02,
        transform: `translate3d(0, ${isVisible ? 0 : 20}px, 0)`,
        filter: isVisible ? 'none' : 'blur(3px)',
        transition:
          'opacity 520ms cubic-bezier(0.22, 1, 0.36, 1), transform 540ms cubic-bezier(0.22, 1, 0.36, 1), filter 460ms cubic-bezier(0.22, 1, 0.36, 1)',
      }}
      className="flex flex-col gap-[4px] will-change-[transform,opacity,filter]"
    >
      <div
        className="font-solva-serif font-light text-[32px] sm:text-[40px] leading-[1.2] tracking-[-0.05em]"
        style={{ color: 'var(--solva-ink)' }}
      >
        {prefix}
        {displayVal.toFixed(decimals)}
        {suffix}
      </div>
      <div
        className="font-solva-sans text-[14px] leading-[21px]"
        style={{ color: 'var(--solva-muted)' }}
      >
        {label}
      </div>
    </div>
  );
}
