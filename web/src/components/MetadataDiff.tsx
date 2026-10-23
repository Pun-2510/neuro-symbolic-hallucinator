import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

interface Field {
  label: string
  provided?: string | null
  retrieved?: string | null
  similarity?: number
}

interface MetadataDiffProps {
  fields: Field[]
  title?: string
}

/**
 * MetadataDiff - Reference Inspector Metadata Comparison
 *
 * Component hiển thị so sánh metadata giữa citation được cung cấp
 * và metadata được truy xuất từ các nguồn học thuật (Crossref, OpenAlex, Semantic Scholar, CORE).
 */
export function MetadataDiff({ fields, title = 'Metadata Comparison' }: MetadataDiffProps) {
  return (
    <div className="space-y-4">
      <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
        {title}
      </h4>

      {/* Header row */}
      <div className="grid grid-cols-3 gap-4 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-slate-700">
        <div>Field</div>
        <div>Provided</div>
        <div>Retrieved</div>
      </div>

      {/* Data rows */}
      <div className="space-y-0">
        {fields.map((field, index) => {
          const hasMismatch =
            field.provided &&
            field.retrieved &&
            field.provided.toLowerCase() !== field.retrieved.toLowerCase()

          return (
            <div
              key={index}
              className={cn(
                "grid grid-cols-3 gap-4 py-3 text-sm",
                "border-b border-slate-100 dark:border-slate-800 last:border-0"
              )}
            >
              {/* Field label */}
              <div className="font-medium text-slate-600 dark:text-slate-300 flex items-center gap-2">
                <span>{field.label}</span>
                {field.similarity !== undefined && (
                  <Badge variant="outline" className="text-[11px] font-mono px-1.5 py-0">
                    {field.similarity}%
                  </Badge>
                )}
              </div>

              {/* Provided value */}
              <div
                className={cn(
                  "font-mono text-slate-600 dark:text-slate-400",
                  hasMismatch && "text-red-600 dark:text-red-400"
                )}
              >
                {field.provided || "—"}
              </div>

              {/* Retrieved value */}
              <div
                className={cn(
                  "font-mono text-slate-600 dark:text-slate-400",
                  hasMismatch && "text-red-600 dark:text-red-400"
                )}
              >
                {field.retrieved || "—"}
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="pt-2 text-xs text-slate-500 dark:text-slate-400">
        <span className="text-red-500 dark:text-red-400">Red text</span> indicates metadata mismatch
      </div>
    </div>
  )
}
