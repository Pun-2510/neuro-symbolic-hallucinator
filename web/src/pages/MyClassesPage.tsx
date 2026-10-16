import { GraduationCap } from 'lucide-react';

/**
 * MyClassesPage — placeholder for Phase 3.
 *
 * Full implementation lands in Phase 4 (per IMPLEMENTATION_ROADMAP).
 * For now, shows a friendly "coming soon" panel + capability context.
 */
export function MyClassesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center">
          <GraduationCap className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            My Classes
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Quản lý lớp học và theo dõi bài nộp của sinh viên.
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-12 text-center">
        <p className="text-base font-medium text-slate-700 dark:text-slate-300">
          Phase 4 — Implementation in progress
        </p>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
          Trang này sẽ hiển thị danh sách lớp bạn phụ trách, danh sách sinh viên,
          và bài nộp gần đây. Backend API đã sẵn sàng — giao diện đang được xây dựng.
        </p>
      </div>
    </div>
  );
}
