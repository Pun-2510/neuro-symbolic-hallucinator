import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadDropzone } from '@/components/UploadDropzone';
import { api } from '@/api/client';

export function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const result = await api.uploadEssay(file);
      navigate(`/essays/${result.essay_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Upload Essay PDF</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Hệ thống sẽ trích xuất citations, tra cứu qua 4 nguồn (Crossref,
        OpenAlex, Semantic Scholar, arXiv), gán nhãn 4 loại, và tính Citation
        Integrity Score.
      </p>

      <UploadDropzone onFile={handleFile} disabled={uploading} />

      {uploading && (
        <p className="mt-4 text-sm text-muted-foreground">
          Đang phân tích... (có thể mất 10–60 giây tùy số citation)
        </p>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          Lỗi: {error}
        </div>
      )}

      <div className="mt-8 p-4 bg-muted/50 rounded-lg text-sm">
        <h3 className="font-semibold mb-2">4 nhãn citation:</h3>
        <ul className="space-y-1">
          <li>
            <span className="verdict-badge bg-verdict_verified mr-2">✓</span>
            <strong>Verified</strong> — nguồn có thật, metadata khớp
          </li>
          <li>
            <span className="verdict-badge bg-verdict_metadata_error mr-2">△</span>
            <strong>Metadata error</strong> — nguồn có thật nhưng 1+ trường sai
          </li>
          <li>
            <span className="verdict-badge bg-verdict_suspected mr-2">✗</span>
            <strong>Suspected hallucination</strong> — không tìm thấy ở 4 nguồn
          </li>
          <li>
            <span className="verdict-badge bg-verdict_unresolved mr-2">?</span>
            <strong>Unresolved</strong> — chưa đủ bằng chứng
          </li>
        </ul>
      </div>
    </div>
  );
}