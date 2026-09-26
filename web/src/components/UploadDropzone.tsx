import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2, File } from 'lucide-react';

/* ============================================================
   SourceLogic — Upload Dropzone Component
   Based on UX/UI Concept Section 5: New Verification
   ============================================================ */

interface UploadDropzoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
};

const MAX_SIZE = 50 * 1024 * 1024; // 50MB

export function UploadDropzone({ onFile, disabled = false }: UploadDropzoneProps) {
  const [fileName, setFileName] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        setFileName(file.name);
        setIsProcessing(true);
        onFile(file);
        // Reset after a delay to allow the parent to handle the file
        setTimeout(() => {
          setIsProcessing(false);
        }, 1000);
      }
    },
    [onFile]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject, acceptedFiles } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    disabled: disabled || isProcessing,
    multiple: false,
  });

  const acceptedFile = acceptedFiles[0];

  // Get file extension for display
  const getFileExtension = (name: string) => {
    const ext = name.split('.').pop()?.toUpperCase();
    return ext || 'FILE';
  };

  return (
    <div
      {...getRootProps()}
      className={`
        dropzone relative cursor-pointer
        ${isDragActive && !isDragReject ? 'dropzone-active' : ''}
        ${isDragReject ? 'border-destructive bg-destructive/5' : ''}
        ${disabled || isProcessing ? 'dropzone-disabled' : ''}
      `}
    >
      <input {...getInputProps()} />

      {isProcessing ? (
        // Processing state
        <div className="flex flex-col items-center justify-center py-8">
          <Loader2 className="h-10 w-10 text-indigo-600 dark:text-indigo-400 animate-spin mb-4" />
          <p className="text-foreground font-medium">Processing {fileName}...</p>
          <p className="text-sm text-muted-foreground mt-1">
            Extracting citations and references
          </p>
        </div>
      ) : acceptedFile ? (
        // File selected
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-900">
              <FileText className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <p className="font-medium text-foreground">{acceptedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                {(acceptedFile.size / 1024 / 1024).toFixed(2)} MB · {getFileExtension(acceptedFile.name)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="tag tag-success">Ready</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setFileName(null);
              }}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      ) : isDragActive ? (
        // Drag active state
        <div className="flex flex-col items-center justify-center py-8">
          <div className="w-16 h-16 rounded-2xl bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center mb-4">
            <Upload className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p className="text-foreground font-medium text-lg">Drop your document here</p>
          <p className="text-sm text-muted-foreground mt-1">
            Release to start verification
          </p>
        </div>
      ) : (
        // Default state - matches UX/UI Concept Section 5
        <div className="flex flex-col items-center justify-center py-8">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-4">
            <Upload className="h-8 w-8 text-slate-400 dark:text-slate-500" />
          </div>
          <p className="text-foreground font-medium text-lg mb-1">
            Drop your document here
          </p>
          <p className="text-sm text-muted-foreground mb-4">
            or click to browse files
          </p>
          <div className="flex items-center gap-2">
            <span className="tag">PDF</span>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Maximum file size: 50MB
          </p>
        </div>
      )}
    </div>
  );
}
