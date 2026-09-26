import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileSearch, Link2, Database, Shield, ArrowRight, CheckCircle, GitBranch, FileText, Quote, Search, Scale, BookOpen, FileQuestion, AlertTriangle, EyeOff } from 'lucide-react';

/* ============================================================
   SourceLogic — Landing Page Component
   Scroll-driven animations with IntersectionObserver
   ============================================================ */

export function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <LandingHeader />
      <HeroSection />
      <HowItWorksSection />
      <NeuroSymbolicSection />
      <VerificationStatusesSection />
      <MultiSourceSection />
      <CTASection />
      <LandingFooter />
    </div>
  );
}

// Header Component
function LandingHeader() {
  return (
    <header className="border-b border-slate-200 bg-white backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-white">
              <path d="M4 8C4 6.89543 4.89543 6 6 6H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M4 16C4 17.1046 4.89543 18 6 18H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M10 12H14M14 12L12 10M14 12L12 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M17 9L19 11L22 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <span className="font-display text-xl font-bold text-slate-900">SourceLogic</span>
            <span className="hidden sm:inline text-xs text-slate-500 ml-2">Academic Verification</span>
          </div>
        </div>
        <nav className="flex items-center gap-2">
          <Link to="/login" className="btn-ghost text-sm px-4 py-2">Sign in</Link>
        </nav>
      </div>
    </header>
  );
}

// Animated Section Wrapper
function AnimatedSection({
  children,
  className = '',
  animation = 'fade-up',
  delay = 0,
  threshold = 0.1
}: {
  children: React.ReactNode;
  className?: string;
  animation?: 'fade-up' | 'fade-left' | 'fade-right' | 'fade-in';
  delay?: number;
  threshold?: number;
}) {
  const [isVisible, setIsVisible] = useState(false);
  const ref = { current: null as HTMLDivElement | null };

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setIsVisible(true), delay);
          observer.unobserve(element);
        }
      },
      { threshold, rootMargin: '0px 0px -50px 0px' }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [delay, threshold]);

  const animationClasses = {
    'fade-up': isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8',
    'fade-left': isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8',
    'fade-right': isVisible ? 'opacity-100 -translate-x-0' : 'opacity-0 translate-x-8',
    'fade-in': isVisible ? 'opacity-100' : 'opacity-0',
  };

  return (
    <div
      ref={(el) => { ref.current = el; }}
      className={`transition-all duration-1000 ease-out ${animationClasses[animation]} ${className}`}
    >
      {children}
    </div>
  );
}

// Staggered Children Animation
function StaggeredGrid({
  children,
  className = '',
  staggerDelay = 100,
  threshold = 0.1
}: {
  children: React.ReactNode[];
  className?: string;
  staggerDelay?: number;
  threshold?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(0);
  const containerRef = { current: null as HTMLDivElement | null };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          // Reveal children one by one
          children.forEach((_, i) => {
            setTimeout(() => setVisibleCount(i + 1), i * staggerDelay);
          });
          observer.unobserve(container);
        }
      },
      { threshold, rootMargin: '0px 0px -50px 0px' }
    );

    observer.observe(container);
    return () => observer.disconnect();
  }, [children.length, staggerDelay, threshold]);

  return (
    <div ref={(el) => { containerRef.current = el; }} className={className}>
      {Array.isArray(children)
        ? children.slice(0, visibleCount)
        : children}
    </div>
  );
}

// Hero Section
function HeroSection() {
  return (
    <section className="pb-12 pt-16 md:pb-16 md:pt-24 relative overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
      </div>

      <div className="max-w-6xl mx-auto px-6">
        <AnimatedSection className="max-w-3xl mx-auto text-center" animation="fade-up">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 mb-6">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wider">
              Academic Source Verification
            </span>
          </div>
        </AnimatedSection>

        <AnimatedSection animation="fade-up" delay={100}>
          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-bold text-slate-900 mb-6 leading-[1.1] text-center">
            Verify Every Citation.
            <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-indigo-500">
              Trace Every Source.
            </span>
          </h1>
        </AnimatedSection>

        <AnimatedSection animation="fade-up" delay={200}>
          <p className="text-lg md:text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed text-center">
            Detect invalid, mismatched and potentially hallucinated academic references
            with explainable source verification powered by Neuro-Symbolic Logic.
          </p>
        </AnimatedSection>

        <AnimatedSection animation="fade-up" delay={300}>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/login" className="btn-primary text-base px-8 py-4 w-full sm:w-auto">
              Sign in to Get Started
              <ArrowRight className="h-5 w-5" />
            </Link>
            <a href="#how-it-works" className="btn-secondary text-base px-8 py-4 w-full sm:w-auto">
              Learn More
            </a>
          </div>
        </AnimatedSection>
      </div>
    </section>
  );
}

// How It Works Section
function HowItWorksSection() {
  const steps = [
    { icon: FileSearch, title: 'Extract', desc: 'Parse PDF, DOCX or paste text. Automatically detect citations and references.', color: 'bg-indigo-50 text-indigo-600' },
    { icon: Link2, title: 'Link', desc: 'Connect in-text citations to bibliography entries with bidirectional matching.', color: 'bg-emerald-50 text-emerald-600' },
    { icon: Database, title: 'Verify', desc: 'Cross-reference against Crossref, OpenAlex, Semantic Scholar, and CORE.', color: 'bg-amber-50 text-amber-600' },
    { icon: Shield, title: 'Decide', desc: 'Get explainable verdicts with evidence chains and triggered rules.', color: 'bg-slate-100 text-slate-600' },
  ];

  return (
    <section id="how-it-works" className="pt-8 pb-20 md:pt-12 md:pb-28">
      <div className="max-w-6xl mx-auto px-6">
        <AnimatedSection className="text-center mb-16" animation="fade-up">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-slate-900 mb-4">
            How It Works
          </h2>
          <p className="text-slate-600 max-w-xl mx-auto">
            From document upload to explainable verification in minutes.
          </p>
        </AnimatedSection>

        <StaggeredGrid className="grid md:grid-cols-2 lg:grid-cols-4 gap-6" staggerDelay={150}>
          {steps.map((step, i) => (
            <div key={i} className="card text-center group hover:shadow-lg transition-shadow">
              <div className={`w-14 h-14 rounded-2xl ${step.color} flex items-center justify-center mx-auto mb-5 group-hover:scale-110 transition-transform`}>
                <step.icon className="h-7 w-7" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">{step.title}</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </StaggeredGrid>
      </div>
    </section>
  );
}

// Neuro-Symbolic Section
function NeuroSymbolicSection() {
  const features = [
    'Semantic title and author matching',
    'Metadata consistency validation',
    'Hallucination detection',
    'Explainable rule triggers',
  ];

  return (
    <section className="py-20 md:py-28 bg-white border-y border-slate-200">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <AnimatedSection animation="fade-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 mb-6">
              <Scale className="h-4 w-4 text-indigo-600" />
              <span className="text-xs font-semibold text-indigo-700">Neuro-Symbolic AI</span>
            </div>
            <h2 className="font-display text-3xl md:text-4xl font-bold text-slate-900 mb-6">
              Hybrid Verification Approach
            </h2>
            <p className="text-slate-600 mb-8 leading-relaxed">
              Our system combines neural semantic matching with symbolic rule validation
              to provide accurate and explainable verification results.
            </p>
            <div className="space-y-4">
              {features.map((feature, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="p-1 rounded-lg bg-emerald-100 mt-0.5">
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                  </div>
                  <span className="text-sm text-slate-700">{feature}</span>
                </div>
              ))}
            </div>
          </AnimatedSection>

          <AnimatedSection animation="fade-right" delay={200}>
            <VerificationTrace />
          </AnimatedSection>
        </div>
      </div>
    </section>
  );
}

// Verification Statuses Section
function VerificationStatusesSection() {
  const statuses = [
    { icon: CheckCircle, badge: 'VERIFIED', badgeClass: 'verdict-badge-verified', color: 'bg-emerald-100', iconColor: 'text-emerald-600', desc: 'Publication found with consistent metadata across verified sources.' },
    { icon: FileQuestion, badge: 'METADATA ERROR', badgeClass: 'verdict-badge-metadata-error', color: 'bg-amber-100', iconColor: 'text-amber-600', desc: 'Source exists but citation has incorrect or mismatched metadata.' },
    { icon: Link2, badge: 'SOURCE MISMATCH', badgeClass: 'verdict-badge-source-mismatch', color: 'bg-orange-100', iconColor: 'text-orange-600', desc: 'Citation appears to reference a different publication.' },
    { icon: Search, badge: 'LIKELY HALLUCINATED', badgeClass: 'verdict-badge-hallucinated', color: 'bg-red-100', iconColor: 'text-red-600', desc: 'No matching publication found across multiple academic databases.' },
    { icon: CheckCircle, badge: 'LIKELY VERIFIED', badgeClass: 'verdict-badge-likely-verified', color: 'bg-green-100', iconColor: 'text-green-600', desc: 'Strong candidate found but missing some identifiers like DOI.' },
    { icon: Quote, badge: 'UNVERIFIABLE', badgeClass: 'verdict-badge-unverifiable', color: 'bg-slate-100', iconColor: 'text-slate-500', desc: 'Insufficient data to reach a conclusion.', border: 'border-slate-200' },
  ];

  return (
    <section className="py-20 md:py-28 bg-white">
      <div className="max-w-6xl mx-auto px-6">
        <AnimatedSection className="text-center mb-12" animation="fade-up">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-slate-900 mb-4">
            Verification Statuses
          </h2>
          <p className="text-slate-600 max-w-xl mx-auto">
            Every verification result is categorized and explained with clear evidence.
          </p>
        </AnimatedSection>

        <StaggeredGrid className="grid md:grid-cols-2 lg:grid-cols-3 gap-5 max-w-4xl mx-auto" staggerDelay={100}>
          {statuses.map((status, i) => (
            <div key={i} className={`card border ${status.border || 'border-emerald-200'} bg-white`}>
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-xl ${status.color} flex items-center justify-center`}>
                  <status.icon className={`h-5 w-5 ${status.iconColor}`} />
                </div>
                <span className={`verdict-badge ${status.badgeClass} text-sm px-4 py-1.5`}>{status.badge}</span>
              </div>
              <p className="text-sm text-slate-600">{status.desc}</p>
            </div>
          ))}
        </StaggeredGrid>
      </div>
    </section>
  );
}

// Multi-Source Section
function MultiSourceSection() {
  const sources = [
    { name: 'Crossref', desc: 'Journal articles metadata', logo: 'https://assets.crossref.org/logo/crossref-logo-landscape-200.svg', height: 'h-10' },
    { name: 'OpenAlex', desc: 'Wide academic coverage', logo: 'https://upload.wikimedia.org/wikipedia/commons/3/32/OpenAlex_logo_icon.svg', height: 'h-12' },
    { name: 'Semantic Scholar', desc: 'AI-powered research', logo: 'https://cdn.simpleicons.org/semanticscholar/000000', height: 'h-12' },
    { name: 'CORE', desc: 'Open access papers', logo: null, height: 'h-12' },
  ];

  return (
    <section className="py-20 md:py-28 bg-white">
      <div className="max-w-6xl mx-auto px-6">
        <AnimatedSection className="text-center mb-12" animation="fade-up">
          <h2 className="font-display text-3xl md:text-4xl font-bold text-slate-900 mb-4">
            Multi-Source Verification
          </h2>
          <p className="text-slate-600 max-w-xl mx-auto">
            Query academic databases to cross-validate citation metadata.
          </p>
        </AnimatedSection>

        <StaggeredGrid className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6" staggerDelay={100}>
          {sources.map((source, i) => (
            <div key={i} className="card border border-slate-200 bg-white text-center py-6 hover:shadow-lg transition-shadow">
              <div className="flex justify-center mb-4 h-14 items-end">
                {source.logo ? (
                  <img src={source.logo} alt={source.name} className={`${source.height} w-auto object-contain`} />
                ) : (
                  <svg viewBox="0 0 64 64" className={source.height} xmlns="http://www.w3.org/2000/svg">
                    <circle cx="32" cy="32" r="30" fill="#F47B20" />
                    <g fill="white">
                      <path d="M32 14 L48 22 L48 38 L32 46 L16 38 L16 22 Z" opacity="0.95" />
                      <path d="M32 20 L42 25 L42 35 L32 40 L22 35 L22 25 Z" fill="#F47B20" />
                    </g>
                  </svg>
                )}
              </div>
              <p className="font-bold text-lg text-slate-900">{source.name}</p>
              <p className="text-sm text-slate-500 mt-1">{source.desc}</p>
            </div>
          ))}
        </StaggeredGrid>
      </div>
    </section>
  );
}

// Verification Trace Demo - Animated Loading Sequence
function VerificationTrace() {
  const [visibleSteps, setVisibleSteps] = useState(0);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const sequence = async () => {
      // Reset
      setVisibleSteps(0);
      await new Promise((r) => setTimeout(r, 500));

      // Step 1: Citation detected
      setVisibleSteps(1);
      await new Promise((r) => setTimeout(r, 800));

      // Step 2: Searching databases
      setVisibleSteps(2);
      await new Promise((r) => setTimeout(r, 1000));

      // Step 3: Matching metadata
      setVisibleSteps(3);
      await new Promise((r) => setTimeout(r, 1000));

      // Step 4: Cross-validating sources
      setVisibleSteps(4);
      await new Promise((r) => setTimeout(r, 800));

      // Step 5: VERIFIED final verdict
      setVisibleSteps(5);
      await new Promise((r) => setTimeout(r, 3000));

      // Loop
      timer = setTimeout(sequence, 0);
    };
    sequence();

    return () => clearTimeout(timer);
  }, []);

  const steps = [
    { id: 1, icon: 'check', text: 'Citation detected' },
    { id: 2, icon: 'pulse', text: 'Searching databases...' },
    { id: 3, icon: 'pulse', text: 'Matching metadata...' },
    { id: 4, icon: 'check', text: 'Cross-validating sources' },
  ];

  return (
    <div className="bg-slate-900 rounded-2xl p-8 font-mono text-sm">
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-slate-400">
          <GitBranch className="h-4 w-4" />
          <span className="text-xs uppercase tracking-wider">Verification Trace</span>
        </div>
        <div className="pl-6 border-l-2 border-slate-700 space-y-4">
          {steps.map((step) => {
            const isVisible = visibleSteps >= step.id;
            const isActive = visibleSteps === step.id && step.icon === 'pulse';
            return (
              <div
                key={step.id}
                className={`flex items-center gap-2 transition-all duration-500 ${
                  isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'
                }`}
              >
                {step.icon === 'check' ? (
                  <span className="text-emerald-400">&#10003;</span>
                ) : (
                  <span className={`text-indigo-400 ${isActive ? 'animate-pulse' : ''}`}>&#8594;</span>
                )}
                <span className="text-slate-300">{step.text}</span>
              </div>
            );
          })}

          {/* Final verdict */}
          <div
            className={`pt-4 mt-4 border-t border-slate-700 transition-all duration-700 ${
              visibleSteps >= 5 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              <span className="text-emerald-400 font-semibold">VERIFIED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// CTA Section
function CTASection() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0" style={{
        background: 'repeating-linear-gradient(0deg, #f8fafc 0px, #f8fafc 40px, #f1f5f9 40px, #f1f5f9 80px)'
      }} />
      <div className="relative max-w-4xl mx-auto px-6 py-20 md:py-28 text-center">
        <AnimatedSection animation="fade-up">
          <h2 className="font-display text-3xl md:text-4xl lg:text-5xl font-bold text-slate-900 mb-6">
            Ready to verify your citations?
          </h2>
        </AnimatedSection>
        <AnimatedSection animation="fade-up" delay={100}>
          <p className="text-lg text-slate-600 mb-10 max-w-2xl mx-auto">
            Upload any academic document and get an explainable verification report
            with evidence chains and rule triggers.
          </p>
        </AnimatedSection>
        <AnimatedSection animation="fade-up" delay={200}>
          <Link
            to="/login"
            className="inline-flex items-center gap-3 px-8 py-4 rounded-2xl font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-lg shadow-indigo-500/25"
          >
            Sign in to Start Verification
            <ArrowRight className="h-5 w-5" />
          </Link>
        </AnimatedSection>
      </div>
    </section>
  );
}

// Footer
function LandingFooter() {
  return (
    <footer className="py-10 border-t border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-white">
                <path d="M4 8C4 6.89543 4.89543 6 6 6H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M4 16C4 17.1046 4.89543 18 6 18H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M10 12H14M14 12L12 10M14 12L12 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M17 9L19 11L22 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <span className="font-display text-lg font-bold text-slate-900">SourceLogic</span>
              <p className="text-xs text-slate-500">Academic Source Verification</p>
            </div>
          </div>
          <div className="flex items-center gap-6 text-sm text-slate-500">
            <Link to="/login" className="hover:text-slate-900 transition-colors">Sign In</Link>
            <span className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Decision Support System
            </span>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-slate-200 text-center">
          <p className="text-xs text-slate-400 max-w-2xl mx-auto">
            This system assists human review — it does not automatically conclude academic fraud.
            All verdicts require human judgment. Not an automated grader.
          </p>
        </div>
      </div>
    </footer>
  );
}
