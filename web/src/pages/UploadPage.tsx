import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { api } from '../api/client';

/* ============================================================
   SourceLogic — Upload Page Component
   Based on UX/UI Concept Section 5: New Verification
   Academic Source Verification Workspace

   Mental Model: "Debugger cho citation"
   - Document = source code
   - Citation = reference call
   - Bibliography = dependency registry
   - Neuro-symbolic checker = linter/static analyzer
   ============================================================ */

const ACCEPTED_EXTENSIONS = ['.pdf'];
const ACCEPTED_MIME = { 'application/pdf': ['.pdf'] };

export function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      // Validate file extension — PDF only
      const ext = droppedFile.name.substring(droppedFile.name.lastIndexOf('.')).toLowerCase();
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        setError('Only PDF files are supported. Please upload a .pdf document.');
        return;
      }
      setError(null);
      setFile(droppedFile);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const picked = e.target.files[0];
      const ext = picked.name.substring(picked.name.lastIndexOf('.')).toLowerCase();
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        setError('Only PDF files are supported. Please upload a .pdf document.');
        return;
      }
      setError(null);
      setFile(picked);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const response = await api.uploadEssay(file);
      // Navigate to processing page with essay_id for async polling
      navigate(`/verification/processing/${response.essay_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed. Please try again.');
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-white mb-2">
          New Verification
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          Upload your document to begin citation and reference verification.
        </p>
      </div>

      {/* Dropzone - UX/UI Concept Section 5 */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 cursor-pointer
          ${dragActive
            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50 scale-[1.02]'
            : file
              ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/30'
              : 'border-slate-300 dark:border-slate-600 hover:border-indigo-400 dark:hover:border-indigo-500 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          }
        `}
      >
        <input
          type="file"
          accept={Object.values(ACCEPTED_MIME).flat().join(',')}
          onChange={handleChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />

        {file ? (
          /* File selected state */
          <div className="flex items-center justify-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center">
              <FileText className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div className="text-left">
              <p className="font-semibold text-slate-900 dark:text-white">{file.name}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
                setError(null);
              }}
              className="ml-auto p-2 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              <X className="h-5 w-5 text-slate-500 dark:text-slate-400" />
            </button>
          </div>
        ) : (
          /* Dropzone default state */
          <>
            <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950 flex items-center justify-center mx-auto mb-4">
              <Upload className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
            </div>
            <p className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
              Drop your document here
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              PDF only
            </p>
            <span className="text-sm text-indigo-600 dark:text-indigo-400 font-medium">
              or browse file
            </span>
          </>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-4 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Submit Button */}
      <div className="mt-10 flex justify-end">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`
            inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all
            ${!file || uploading
              ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow-md'
            }
          `}
        >
          {uploading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              Start Verification
              <Upload className="h-5 w-5" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
