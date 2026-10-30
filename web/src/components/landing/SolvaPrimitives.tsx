import { useState, useEffect, useRef, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

/* ============================================================
   SOLVA EDITORIAL PRIMITIVES — CITRA (SourceLogic)
   Exact 1:1 Visual & Interactive Building Blocks
   ============================================================ */

export type Lang = 'en' | 'vi';

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
  );
}

/**
 * 2. Two-Tone Editorial Split Heading (H1 / H2)
 * Uses Sentient Light (font-weight: 300), line-height: 1.05, letter-spacing: -0.05em.
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
  const sizeClass =
    size === 'h1'
      ? 'text-[40px] sm:text-[48px] xl:text-[56px] leading-[1.06] tracking-[-0.05em]'
      : 'text-[34px] sm:text-[40px] xl:text-[48px] leading-[1.06] tracking-[-0.05em]';

  return (
    <Tag
      className={`font-solva-serif font-light ${sizeClass} ${
        centered ? 'text-center mx-auto' : ''
      } ${className}`}
    >
      <span className="block" style={{ color: 'var(--solva-ink)' }}>
        {primary}
      </span>
      {secondary && (
        <span className="block" style={{ color: 'var(--solva-muted)' }}>
          {secondary}
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
  return (
    <div className={`relative overflow-hidden ${radiusClass} ${className}`}>
      <img
        src={paintingSrc}
        alt={alt}
        loading="eager"
        decoding="async"
        className="absolute inset-0 w-full h-full object-cover pointer-events-none select-none"
      />
      <div className="solva-noise-overlay" aria-hidden="true" />
      <div className="relative z-10 w-full h-full">{children}</div>
    </div>
  );
}

/**
 * 5. Scroll-Triggered Sticky Stacking Card (`scale(1)` -> `scale(0.92)`)
 * Replicates Solva's Section 3 Sticky Container 1..3 stacking effect.
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

  useEffect(() => {
    if (index >= total - 1) return;

    const handleScroll = () => {
      const el = cardRef.current;
      if (!el) return;
      const parent = el.parentElement;
      if (!parent) return;
      const nextSibling = parent.children[index + 1] as HTMLElement | undefined;
      if (!nextSibling) return;

      const nextRect = nextSibling.getBoundingClientRect();
      const viewportH = window.innerHeight;
      // Start scaling down when the next sticky card enters the bottom 85% of viewport
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
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [index, total]);

  return (
    <div
      ref={cardRef}
      style={{
        zIndex: index + 1,
        transform: `scale(${scale})`,
        transformOrigin: 'top center',
        backgroundColor: 'var(--solva-surface)',
      }}
      className="lg:sticky lg:top-[116px] w-full rounded-[16px] p-[12px] transition-transform duration-75 ease-out will-change-transform"
    >
      {children}
    </div>
  );
}

/**
 * 6. Scroll-Triggered Animated Count-Up Metric (`Sentient` 40px Light)
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
  const hasAnimated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const duration = 1100;
          const startTime = performance.now();
          const startVal = targetValue * 0.25;

          const tick = (now: number) => {
            const elapsed = now - startTime;
            const progress = Math.min(1, elapsed / duration);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = startVal + (targetValue - startVal) * eased;
            setDisplayVal(current);
            if (progress < 1) {
              requestAnimationFrame(tick);
            } else {
              setDisplayVal(targetValue);
            }
          };
          requestAnimationFrame(tick);
          observer.unobserve(el);
        }
      },
      { threshold: 0.25 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [targetValue]);

  return (
    <div ref={ref} className="flex flex-col gap-[4px]">
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
