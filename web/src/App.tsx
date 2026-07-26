import { Link, Outlet } from 'react-router-dom';
import { DecisionSupportDisclaimer } from '@/components/DecisionSupportDisclaimer';

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-bold">Essay Integrity Checker</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link to="/" className="hover:underline">Upload</Link>
            <Link to="/history" className="hover:underline">History</Link>
          </nav>
        </div>
      </header>

      {/* Disclaimer BẮT BUỘC trên mọi page */}
      <DecisionSupportDisclaimer />

      <main className="container mx-auto px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t mt-12 py-6">
        <div className="container mx-auto px-4 text-sm text-muted-foreground">
          <p>
            Đồ án tốt nghiệp — TDTU. Citation-only validation. Hệ thống không tự
            động kết luận gian lận học thuật.
          </p>
        </div>
      </footer>
    </div>
  );
}