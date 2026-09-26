import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Check, Loader2, Circle, FileText, Quote, Link, Database, GitMerge, FileCheck } from 'lucide-react';
import { api, type AnalysisReport } from '@/api/client';

/* ============================================================
   SourceLogic — Processing Page
   Based on UX/UI Concept Section 6: Processing Screen
   Visual pipeline for verification process

   Mental Model: "Debugger cho citation"
   - Shows real-time pipeline progress
   - Displays extraction stats (citations, references, linked)
   - Shows retrieval source results
   - Polls backend for real-time status updates
   ============================================================ */

interface StepData {
  label: string;
  details?: string;
}

export function ProcessingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pollCount, setPollCount] = useState(0);

  // Pipeline steps from UX/UI Concept Section 6
  const steps: StepData[] = [
    { label: 'Parsing document', details: 'Extracting text and structure from PDF' },
    { label: 'Detecting citation style', details: 'APA · IEEE · Harvard · MLA · Chicago' },
    { label: 'Extracting citations & references', details: 'Scanning for in-text citations and bibliography' },
    { label: 'Linking citations to references', details: 'Bidirectional citation-reference matching' },
    { label: 'Retrieving source metadata', details: 'Querying Crossref, OpenAlex, Semantic Scholar, CORE' },
    { label: 'Comparing candidate publications', details: 'Title, author, year, venue matching' },
    { label: 'Applying neuro-symbolic rules', details: 'Evidence-based verification logic' },
    { label: 'Generating verification report', details: 'Compiling findings and explanations' },
  ];

  // Poll backend for real-time report data
  useEffect(() => {
    if (!id) return;

    const pollInterval = setInterval(async () => {
      try {
        const data = await api.getEssay(Number(id));
        setReport(data);
        setPollCount((c) => c + 1);

        // If we have verdicts, processing is complete
        if (data.verdicts && data.verdicts.length > 0) {
          setIsComplete(true);
          clearInterval(pollInterval);
          // Navigate to report after a short delay
          setTimeout(() => navigate(`/verification/report/${id}`), 1500);
        }
      } catch (e) {
        // Report not ready yet - this is expected during processing
        console.log('Report not ready, polling continues...');
        setPollCount((c) => c + 1);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [id, navigate]);

  // Progress through steps based on poll count (visual feedback)
  useEffect(() => {
    if (isComplete) return;

    // Simulate step progression based on poll attempts
    const stepIndex = Math.min(Math.floor(pollCount / 1.5), steps.length - 1);
    setCurrentStep(stepIndex);

    // Mark complete after enough polls or if we have data
    if (pollCount >= steps.length * 1.5 || report?.verdicts) {
      setIsComplete(true);
    }
  }, [pollCount, isComplete, report, steps.length]);

  // Calculate progress percentage
  const progress = Math.round(((currentStep + 1) / steps.length) * 100);

  // Get status for each step
  const getStepStatus = (index: number): 'completed' | 'active' | 'pending' | 'error' => {
    if (index < currentStep) return 'completed';
    if (index === currentStep) return 'active';
    return 'pending';
  };

  // Get status icon
  const getStatusIcon = (status: 'completed' | 'active' | 'pending' | 'error') => {
    switch (status) {
      case 'completed':
        return <Check className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />;
      case 'active':
        return <Loader2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400 animate-spin" />;
      case 'error':
        return <Circle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      default:
        return <Circle className="h-4 w-4 text-slate-300 dark:text-slate-600" />;
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header - UX/UI Concept Section 6 */}
      <div className="text-center mb-10">
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-white mb-3">
          Analyzing document
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          This may take a few minutes depending on document size.
        </p>
      </div>

      {/* Progress Bar */}
      <div className="mb-10">
        <div className="h-2.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-600 to-indigo-500 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between items-center mt-2">
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {isComplete ? 'Complete' : 'Processing...'}
          </span>
          <span className="text-sm font-mono font-semibold text-slate-600 dark:text-slate-300">
            {progress}%
          </span>
        </div>
      </div>

      {/* Pipeline Steps - UX/UI Concept Section 6 */}
      <div className="card bg-white dark:bg-slate-800/50 p-6 mb-6">
        <div className="flex items-center gap-2 mb-5">
          <GitMerge className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">
            Verification Pipeline
          </h2>
        </div>

        <div className="space-y-3">
          {steps.map((step, index) => {
            const status = getStepStatus(index);
            const isExtractionStep = index === 2;
            const isLinkingStep = index === 3;

            return (
              <div key={index} className="flex items-start gap-3">
                {/* Status indicator */}
                <div
                  className={`mt-0.5 w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-300 ${
                    status === 'completed'
                      ? 'bg-emerald-100 dark:bg-emerald-900/50'
                      : status === 'active'
                      ? 'bg-indigo-100 dark:bg-indigo-900/50'
                      : status === 'error'
                      ? 'bg-red-100 dark:bg-red-900/50'
                      : 'bg-slate-100 dark:bg-slate-800'
                  }`}
                >
                  {getStatusIcon(status)}
                </div>

                {/* Step content */}
                <div className="flex-1 min-w-0 pt-1">
                  <p
                    className={`text-sm transition-colors duration-200 ${
                      status === 'completed'
                        ? 'text-emerald-700 dark:text-emerald-300'
                        : status === 'active'
                        ? 'text-indigo-700 dark:text-indigo-300 font-semibold'
                        : status === 'error'
                        ? 'text-red-700 dark:text-red-300'
                        : 'text-slate-400 dark:text-slate-500'
                    }`}
                  >
                    {step.label}
                  </p>

                  {/* Show extraction stats when on step 2+ */}
                  {isExtractionStep && status !== 'pending' && report && (
                    <div className="flex gap-4 mt-2 text-xs">
                      <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                        <Quote className="h-3 w-3" />
                        {report.num_citations} citations
                      </span>
                      <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400">
                        <FileText className="h-3 w-3" />
                        {report.linking_summary.matched + report.linking_summary.missing_reference + report.linking_summary.uncited_reference} references
                      </span>
                    </div>
                  )}

                  {/* Show linking stats when on step 3+ */}
                  {isLinkingStep && status !== 'pending' && report && (
                    <div className="flex gap-4 mt-2 text-xs">
                      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <Link className="h-3 w-3" />
                        {report.linking_summary.matched} linked
                      </span>
                      <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                        <Circle className="h-3 w-3" />
                        {report.linking_summary.unresolved} unresolved
                      </span>
                    </div>
                  )}

                  {/* Active step details */}
                  {status === 'active' && step.details && (
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                      {step.details}
                    </p>
                  )}
                </div>

                {/* Step counter */}
                <span className="text-xs font-mono text-slate-400 dark:text-slate-500 pt-1">
                  {index + 1}/{steps.length}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stats Grid - UX/UI Concept Section 6 */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {/* Citations */}
        <div className="card bg-white dark:bg-slate-800/50 p-4 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/50 mb-3">
            <Quote className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {report?.num_citations ?? '-'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Citations</p>
        </div>

        {/* References */}
        <div className="card bg-white dark:bg-slate-800/50 p-4 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-700 mb-3">
            <FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {report ? report.linking_summary.matched + report.linking_summary.missing_reference + report.linking_summary.uncited_reference : '-'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">References</p>
        </div>

        {/* Linked */}
        <div className="card bg-white dark:bg-slate-800/50 p-4 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 mb-3">
            <Link className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
            {report?.linking_summary.matched ?? '-'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Linked</p>
        </div>

        {/* Unresolved */}
        <div className="card bg-white dark:bg-slate-800/50 p-4 text-center">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/50 mb-3">
            <Circle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">
            {report?.linking_summary.unresolved ?? '-'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Unresolved</p>
        </div>
      </div>

      {/* Retrieval Sources - UX/UI Concept Section 18 */}
      <div className="card bg-white dark:bg-slate-800/50 p-6 mt-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          <h3 className="font-display text-base font-semibold text-slate-900 dark:text-slate-100">
            Source Retrieval
          </h3>
          {!report && <Loader2 className="h-4 w-4 animate-spin text-indigo-600 ml-2" />}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {/* Crossref */}
          <div className={`p-3 rounded-xl border transition-all duration-300 ${
            report ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800' : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
          }`}>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Crossref</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {report ? (
                <span className="text-emerald-600 dark:text-emerald-400">
                  {report.verdicts.filter(v => v.matched_sources.some(s => s.source === 'crossref')).length} verified
                </span>
              ) : 'Querying...'}
            </p>
          </div>

          {/* OpenAlex */}
          <div className={`p-3 rounded-xl border transition-all duration-300 ${
            report ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800' : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
          }`}>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">OpenAlex</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {report ? (
                <span className="text-emerald-600 dark:text-emerald-400">
                  {report.verdicts.filter(v => v.matched_sources.some(s => s.source === 'openalex')).length} verified
                </span>
              ) : 'Querying...'}
            </p>
          </div>

          {/* Semantic Scholar */}
          <div className={`p-3 rounded-xl border transition-all duration-300 ${
            report ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800' : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
          }`}>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Semantic Scholar</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {report ? (
                <span className="text-emerald-600 dark:text-emerald-400">
                  {report.verdicts.filter(v => v.matched_sources.some(s => s.source === 's2')).length} verified
                </span>
              ) : 'Querying...'}
            </p>
          </div>

          {/* CORE */}
          <div className={`p-3 rounded-xl border transition-all duration-300 ${
            report ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800' : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
          }`}>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">CORE</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {report ? (
                <span className="text-emerald-600 dark:text-emerald-400">
                  {report.verdicts.filter(v => v.matched_sources.some(s => s.source === 'core')).length} verified
                </span>
              ) : 'Querying...'}
            </p>
          </div>
        </div>
      </div>

      {/* Completion Message */}
      {isComplete && (
        <div className="mt-8 p-6 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/50 mb-3">
            <FileCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
          </div>
          <h3 className="font-display text-lg font-semibold text-emerald-800 dark:text-emerald-200 mb-1">
            Analysis Complete
          </h3>
          <p className="text-sm text-emerald-600 dark:text-emerald-400">
            Redirecting to verification report...
          </p>
        </div>
      )}
    </div>
  );
}
