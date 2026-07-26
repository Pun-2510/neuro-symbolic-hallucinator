import { AlertCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '@/api/client';

/**
 * DecisionSupportDisclaimer — BẮT BUỘC trên mọi page.
 *
 * Lấy disclaimer text từ backend /api/health endpoint.
 */
export function DecisionSupportDisclaimer() {
  const [disclaimer, setDisclaimer] = useState<string>(
    'Decision-support only — not a final grade.'
  );

  useEffect(() => {
    api
      .health()
      .then((h) => setDisclaimer(h.disclaimer))
      .catch(() => {
        /* keep default */
      });
  }, []);

  return (
    <div className="bg-amber-50 border-y border-amber-200">
      <div className="container mx-auto px-4 py-2 flex items-start gap-2 text-sm text-amber-900">
        <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <span>
          <strong>⚠️ Decision-support only.</strong> {disclaimer} Hệ thống{' '}
          <strong>CHỈ kiểm tra trích dẫn</strong> — KHÔNG chấm điểm toàn bài
          tiểu luận.
        </span>
      </div>
    </div>
  );
}