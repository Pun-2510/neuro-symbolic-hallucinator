import { cn } from "@/lib/utils"

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
 *
 * Theo design concept: "Debugger cho citation"
 * - Field = field name
 * - Provided = metadata từ citation trong document
 * - Retrieved = metadata được tìm thấy từ academic databases
 * - Mismatch được highlight để dễ phát hiện
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
              <div className="font-medium text-slate-600 dark:text-slate-300">
                {field.label}
                {field.similarity !== undefined && (
                  <span className="ml-2 text-xs text-slate-400">
                    {field.similarity}%
                  </span>
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
