import { useCallback, useRef, useState } from 'react';
import { Upload, X, Loader2, ImageIcon } from 'lucide-react';
import { api } from '@/api/client';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_BYTES = 2 * 1024 * 1024; // 2MB

interface AvatarUploadProps {
  currentAvatarUrl: string | null;
  onSuccess: (user: import('@/api/client').User) => void;
  size?: 'sm' | 'md' | 'lg';
}

export function AvatarUpload({ currentAvatarUrl, onSuccess, size = 'md' }: AvatarUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);

  const sizeClasses = {
    sm: 'w-16 h-16',
    md: 'w-24 h-24',
    lg: 'w-32 h-32',
  };

  const handleFileSelect = (file: File) => {
    setError('');
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError('Only JPG, PNG, and WEBP images are allowed.');
      return;
    }
    if (file.size > MAX_BYTES) {
      setError('File size must be under 2MB.');
      return;
    }
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError('');
    try {
      const user = await api.uploadMyAvatar(selectedFile);
      onSuccess(user);
      setSelectedFile(null);
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreview(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const displayUrl = preview || currentAvatarUrl;

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Avatar preview */}
      <div
        className={`${sizeClasses[size]} rounded-full overflow-hidden bg-slate-100 dark:bg-slate-800 border-2 border-dashed border-slate-300 dark:border-slate-600 flex items-center justify-center cursor-pointer transition-colors ${
          dragging ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950' : ''
        } ${selectedFile ? 'border-indigo-400' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        {displayUrl ? (
          <img
            src={displayUrl}
            alt="Avatar preview"
            className="w-full h-full object-cover"
          />
        ) : (
          <ImageIcon className="h-8 w-8 text-slate-400" />
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        onChange={handleInputChange}
        className="hidden"
      />

      {error && (
        <p className="text-xs text-red-600 dark:text-red-400 text-center">{error}</p>
      )}

      {selectedFile ? (
        <div className="flex flex-col items-center gap-2">
          <p className="text-xs text-slate-500 dark:text-slate-400 truncate max-w-[10rem]">
            {(selectedFile.size / 1024).toFixed(1)} KB
          </p>
          <div className="flex gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); handleClear(); }}
              disabled={uploading}
              className="btn-ghost text-xs py-1 px-3"
            >
              <X className="h-3 w-3" />
              Cancel
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); handleUpload(); }}
              disabled={uploading}
              className="btn-primary btn-sm"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-3 w-3" />
                  Upload
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Click or drag to upload
        </p>
      )}
    </div>
  );
}
