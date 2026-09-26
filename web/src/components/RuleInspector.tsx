import { cn } from "@/lib/utils"
import { FileCode, ChevronRight, CheckCircle, XCircle, AlertTriangle } from "lucide-react"

/* ============================================================
   SourceLogic — Rule Inspector Component
   Based on UX/UI Concept Section 15: Rule Inspector
   ============================================================ */

interface Rule {
  id: string
  name: string
  description: string
  conditions: {
    field: string
    operator: string
    value: string | number
  }[]
  conclusion: string
  triggered: boolean
}

interface RuleInspectorProps {
  triggeredRules: string[]
  verdictLabel?: string
  className?: string
}

// Rule definitions with condition logic (from rules.py)
const RULE_DEFINITIONS: Record<string, Omit<Rule, "triggered">> = {
  // High priority pre-flight rules
  "R-FAKE-URL": {
    id: "R-FAKE-URL",
    name: "Fake URL Detection",
    description: "URL domain is clearly fake/non-academic (example.com, test.com, localhost, etc.)",
    conditions: [
      { field: "url_domain", operator: "IN", value: "[fake_domains]" },
    ],
    conclusion: "SUSPECTED_HALLUCINATION",
  },
  "R-FABRICATED-DOI": {
    id: "R-FABRICATED-DOI",
    name: "Fabricated DOI Pattern",
    description: "DOI matches known fabricated DOI pattern (invalid publisher prefix like 10.1234, 10.9999)",
    conditions: [
      { field: "doi_pattern", operator: "MATCHES", value: "[fabricated_patterns]" },
    ],
    conclusion: "SUSPECTED_HALLUCINATION",
  },
  "R-FAKE-AUTHOR": {
    id: "R-FAKE-AUTHOR",
    name: "Fake Author Name",
    description: "Author name matches fake/fabricated patterns (fictional, example, test author, etc.)",
    conditions: [
      { field: "author_pattern", operator: "MATCHES", value: "[fake_author_regex]" },
    ],
    conclusion: "SUSPECTED_HALLUCINATION",
  },
  "R-FUTURE-YEAR": {
    id: "R-FUTURE-YEAR",
    name: "Future Year Detection",
    description: "Citation year is in the future with unknown author - likely fabricated",
    conditions: [
      { field: "cited_year", operator: ">", value: "current_year" },
      { field: "author", operator: "NOT IN", value: "[known_authors]" },
    ],
    conclusion: "SUSPECTED_HALLUCINATION",
  },
  "R-FUTURE-YEAR-KNOWN-AUTHOR": {
    id: "R-FUTURE-YEAR-KNOWN-AUTHOR",
    name: "Future Year - Known Author",
    description: "Citation year is in the future but author is known - likely metadata error",
    conditions: [
      { field: "cited_year", operator: ">", value: "current_year" },
      { field: "author", operator: "IN", value: "[known_authors]" },
    ],
    conclusion: "METADATA_ERROR",
  },
  // Core verification rules
  "R-DOI-TITLE-AUTHOR": {
    id: "R-DOI-TITLE-AUTHOR",
    name: "DOI + Title + Author Match",
    description: "Exact DOI match with high title similarity and author overlap",
    conditions: [
      { field: "doi_exact_match", operator: "=", value: "true" },
      { field: "title_sim", operator: ">=", value: "0.70" },
      { field: "author_jaccard", operator: ">=", value: "0.40" },
    ],
    conclusion: "VERIFIED",
  },
  "R-WELL-LINKED": {
    id: "R-WELL-LINKED",
    name: "Well-Linked Citation (High Similarity)",
    description: "Citation is author-year matched with high title similarity",
    conditions: [
      { field: "mapping_status", operator: "=", value: "matched" },
      { field: "title_sim", operator: ">=", value: "0.70" },
    ],
    conclusion: "VERIFIED",
  },
  "R-WELL-LINKED-MODERATE": {
    id: "R-WELL-LINKED-MODERATE",
    name: "Well-Linked Citation (Moderate Similarity)",
    description: "Citation is author-year matched with moderate title similarity",
    conditions: [
      { field: "mapping_status", operator: "=", value: "matched" },
      { field: "title_sim", operator: "BETWEEN", value: "[0.50, 0.70)" },
    ],
    conclusion: "VERIFIED (with metadata note)",
  },
  "R-DOI-TITLE-MISMATCH": {
    id: "R-DOI-TITLE-MISMATCH",
    name: "DOI Match with Title Mismatch",
    description: "DOI resolves but title similarity is moderate",
    conditions: [
      { field: "doi_exact_match", operator: "=", value: "true" },
      { field: "title_sim", operator: "BETWEEN", value: "[0.50, 0.70)" },
    ],
    conclusion: "METADATA_ERROR",
  },
  "R-CONSENSUS-FULL": {
    id: "R-CONSENSUS-FULL",
    name: "Full Source Consensus",
    description: "Multiple sources agree on title, author, and year",
    conditions: [
      { field: "consensus", operator: ">=", value: "2" },
      { field: "title_sim", operator: ">=", value: "0.70" },
      { field: "author_jaccard", operator: ">=", value: "0.40" },
      { field: "year_distance", operator: "<=", value: "1" },
    ],
    conclusion: "VERIFIED",
  },
  "R-CONSENSUS-PARTIAL": {
    id: "R-CONSENSUS-PARTIAL",
    name: "Partial Source Consensus",
    description: "Multiple sources agree but some fields differ",
    conditions: [
      { field: "consensus", operator: ">=", value: "2" },
      { field: "title_sim", operator: ">=", value: "0.70" },
    ],
    conclusion: "METADATA_ERROR",
  },
  "R-KNOWN-AUTHOR-TITLE-MISMATCH": {
    id: "R-KNOWN-AUTHOR-TITLE-MISMATCH",
    name: "Known Author with Title Mismatch",
    description: "Known academic author but title similarity is moderate",
    conditions: [
      { field: "author", operator: "IN", value: "[known_authors]" },
      { field: "title_sim", operator: "BETWEEN", value: "[0.30, 0.70)" },
      { field: "sources_succeeded", operator: ">", value: "0" },
    ],
    conclusion: "METADATA_ERROR",
  },
  "R-KNOWN-AUTHOR-WEAK-EVIDENCE": {
    id: "R-KNOWN-AUTHOR-WEAK-EVIDENCE",
    name: "Known Author - Weak Evidence",
    description: "Known author found but evidence is weak (low similarity scores)",
    conditions: [
      { field: "author", operator: "IN", value: "[known_authors]" },
      { field: "title_sim", operator: "BETWEEN", value: "[0.20, 0.70)" },
      { field: "sources_found", operator: ">", value: "0" },
    ],
    conclusion: "METADATA_ERROR",
  },
  "R-CONTENT-ALIGNMENT": {
    id: "R-CONTENT-ALIGNMENT",
    name: "Neural Content Alignment",
    description: "Neural layer verified semantic alignment between citation context and source content",
    conditions: [
      { field: "content_alignment_score", operator: ">", value: "0" },
      { field: "content_is_aligned", operator: "=", value: "true" },
      { field: "title_sim", operator: ">=", value: "0.50" },
    ],
    conclusion: "VERIFIED",
  },
  "R-CONTENT-MISMATCH": {
    id: "R-CONTENT-MISMATCH",
    name: "Content Mismatch",
    description: "Title matches but neural content alignment failed - potential misattribution",
    conditions: [
      { field: "content_is_aligned", operator: "=", value: "false" },
      { field: "content_alignment_score", operator: ">=", value: "0.30" },
      { field: "title_sim", operator: ">=", value: "0.70" },
    ],
    conclusion: "SUSPECTED_HALLUCINATION",
  },
  "R-STYLE-INCONSISTENT": {
    id: "R-STYLE-INCONSISTENT",
    name: "Citation Style Inconsistency",
    description: "In-text citation style does not match detected document style",
    conditions: [
      { field: "style_profile", operator: "=", value: "MIXED" },
    ],
    conclusion: "Confidence penalty applied",
  },
  "R-AMBIGUOUS-MAPPING": {
    id: "R-AMBIGUOUS-MAPPING",
    name: "Ambiguous Citation-Reference Mapping",
    description: "Linker could not determine which reference entry matches the citation",
    conditions: [
      { field: "mapping_status", operator: "=", value: "ambiguous_mapping" },
    ],
    conclusion: "UNRESOLVED",
  },
  "R-ABSTENTION-BORDER": {
    id: "R-ABSTENTION-BORDER",
    name: "Abstention Border Zone",
    description: "Title similarity is in the uncertain range - system refuses to conclude",
    conditions: [
      { field: "title_sim", operator: "BETWEEN", value: "[0.40, 0.50]" },
    ],
    conclusion: "UNRESOLVED",
  },
  "R-DOMAIN-EXCEPTION": {
    id: "R-DOMAIN-EXCEPTION",
    name: "Domain Exception",
    description: "DOI matches but title similarity is low - URL may be broken",
    conditions: [
      { field: "doi_exact_match", operator: "=", value: "true" },
      { field: "title_sim", operator: "<", value: "0.50" },
      { field: "consensus", operator: ">=", value: "2" },
    ],
    conclusion: "METADATA_ERROR (flagged)",
  },
  "R-FAIL-ALL": {
    id: "R-FAIL-ALL",
    name: "All APIs Failed",
    description: "All external APIs failed completely - no evidence available",
    conditions: [
      { field: "sources_failed", operator: ">", value: "0" },
      { field: "sources_succeeded", operator: "=", value: "0" },
    ],
    conclusion: "UNRESOLVED",
  },
  "R-NO-CANDIDATE": {
    id: "R-NO-CANDIDATE",
    name: "No Matching Candidates",
    description: "No candidates found across all 4 academic databases",
    conditions: [
      { field: "candidates", operator: "=", value: "0" },
    ],
    conclusion: "UNRESOLVED",
  },
  "R-WEAK-EVIDENCE": {
    id: "R-WEAK-EVIDENCE",
    name: "Weak Evidence Fallback",
    description: "Some candidates found but similarity scores are too low for verification",
    conditions: [
      { field: "title_sim", operator: "<", value: "0.70" },
      { field: "author_jaccard", operator: "<", value: "0.40" },
    ],
    conclusion: "UNRESOLVED",
  },
}

// Get verdict color based on conclusion
function getVerdictColorClass(conclusion: string): {
  bg: string
  border: string
  text: string
  icon: React.ReactNode
} {
  if (conclusion.includes("VERIFIED")) {
    return {
      bg: "bg-emerald-50 dark:bg-emerald-950",
      border: "border-emerald-200 dark:border-emerald-800",
      text: "text-emerald-700 dark:text-emerald-300",
      icon: <CheckCircle className="h-3.5 w-3.5" />,
    }
  }
  if (conclusion.includes("METADATA_ERROR")) {
    return {
      bg: "bg-amber-50 dark:bg-amber-950",
      border: "border-amber-200 dark:border-amber-800",
      text: "text-amber-700 dark:text-amber-300",
      icon: <AlertTriangle className="h-3.5 w-3.5" />,
    }
  }
  if (conclusion.includes("HALLUCINATION")) {
    return {
      bg: "bg-red-50 dark:bg-red-950",
      border: "border-red-200 dark:border-red-800",
      text: "text-red-700 dark:text-red-300",
      icon: <XCircle className="h-3.5 w-3.5" />,
    }
  }
  return {
    bg: "bg-slate-50 dark:bg-slate-800",
    border: "border-slate-200 dark:border-slate-700",
    text: "text-slate-700 dark:text-slate-300",
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
  }
}

export function RuleInspector({
  triggeredRules,
  verdictLabel,
  className
}: RuleInspectorProps) {
  // Build list of rules with triggered status
  const rules: Rule[] = triggeredRules.map((ruleId) => {
    const definition = RULE_DEFINITIONS[ruleId]
    if (definition) {
      return { ...definition, triggered: true }
    }
    // Unknown rule - create generic definition
    return {
      id: ruleId,
      name: ruleId,
      description: "Custom rule triggered",
      conditions: [],
      conclusion: verdictLabel || "UNKNOWN",
      triggered: true,
    }
  })

  if (rules.length === 0) {
    return (
      <div className={cn("rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4", className)}>
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
          <FileCode className="h-4 w-4" />
          <span className="text-sm">No rules triggered</span>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <FileCode className="h-4 w-4 text-slate-500 dark:text-slate-400" />
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Triggered Rules ({rules.length})
        </h4>
      </div>

      {/* Rule list */}
      <div className="space-y-2">
        {rules.map((rule) => {
          const colors = getVerdictColorClass(rule.conclusion)

          return (
            <div
              key={rule.id}
              className={cn(
                "rounded-lg border p-3",
                colors.bg,
                colors.border
              )}
            >
              {/* Rule header */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={cn("font-mono text-xs font-semibold", colors.text)}>
                      {rule.id}
                    </span>
                  </div>
                  <p className={cn("text-sm font-medium mt-0.5", colors.text)}>
                    {rule.name}
                  </p>
                </div>
                <span className={cn("flex items-center gap-1 text-xs font-medium px-2 py-1 rounded", colors.bg, colors.border, colors.text)}>
                  {colors.icon}
                  <span className="text-[10px]">{rule.conclusion}</span>
                </span>
              </div>

              {/* Rule description */}
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                {rule.description}
              </p>

              {/* Condition logic */}
              {rule.conditions.length > 0 && (
                <div className="mt-2 p-2 bg-white/50 dark:bg-slate-900/50 rounded border border-slate-200/50 dark:border-slate-700/50">
                  <div className="font-mono text-xs space-y-1">
                    <div className="text-slate-500 dark:text-slate-400 font-semibold">IF</div>
                    {rule.conditions.map((condition, idx) => (
                      <div key={idx} className="flex items-center gap-1 text-slate-600 dark:text-slate-300 pl-3">
                        {idx > 0 && (
                          <span className="text-slate-400 dark:text-slate-500 mr-1">AND</span>
                        )}
                        <span className="font-medium">{condition.field}</span>
                        <span className="text-slate-400">{condition.operator}</span>
                        <span className="text-slate-500">{condition.value}</span>
                      </div>
                    ))}
                    <div className="text-slate-500 dark:text-slate-400 font-semibold mt-2">THEN</div>
                    <div className="pl-3 text-slate-600 dark:text-slate-300">
                      {rule.conclusion}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Compact version for inline use
export function RuleInspectorCompact({
  triggeredRules,
  className
}: {
  triggeredRules: string[]
  className?: string
}) {
  if (triggeredRules.length === 0) {
    return null
  }

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {triggeredRules.map((ruleId) => {
        const definition = RULE_DEFINITIONS[ruleId]
        const conclusion = definition?.conclusion || "UNKNOWN"
        const colors = getVerdictColorClass(conclusion)

        return (
          <span
            key={ruleId}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold border",
              colors.bg,
              colors.border,
              colors.text
            )}
            title={definition?.description || ruleId}
          >
            {colors.icon}
            {ruleId}
          </span>
        )
      })}
    </div>
  )
}
