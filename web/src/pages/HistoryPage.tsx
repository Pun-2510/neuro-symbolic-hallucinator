import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '@/api/client';

interface HistoryItem {
  id: number;
  filename: string;
  num_pages: number;
  uploaded_at: string;
}

export function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    // TODO: cần backend endpoint /essays (list) — hiện tại chưa có
    // Trong thời gian chờ, hard-code empty + hướng dẫn user quay lại Upload
    setItems([]);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">History</h1>
      {items.length === 0 ? (
        <div className="p-6 bg-muted rounded text-sm text-muted-foreground">
          <p>
            Chưa có lịch sử. (TODO: implement backend <code>GET /api/essays</code>{' '}
            để list.)
          </p>
          <Link to="/" className="text-primary underline mt-3 inline-block">
            ← Upload essay mới
          </Link>
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li key={it.id} className="p-3 border rounded">
              <Link to={`/essays/${it.id}`} className="font-medium underline">
                {it.filename}
              </Link>
              <span className="text-sm text-muted-foreground ml-2">
                {it.num_pages} trang · {it.uploaded_at}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}