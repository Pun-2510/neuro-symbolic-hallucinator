import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';
import { cn } from '@/lib/utils';

export function UploadDropzone({
  onFile,
  disabled,
}: {
  onFile: (file: File) => void;
  disabled?: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const onDrop = useCallback(
    (accepted: File[]) => {
      const f = accepted[0];
      if (f) {
        setFile(f);
        onFile(f);
      }
    },
    [onFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
        isDragActive
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/50',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <input {...getInputProps()} />
      <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
      <p className="text-lg font-medium">
        {file ? file.name : 'Kéo thả PDF vào đây hoặc click để chọn'}
      </p>
      <p className="text-sm text-muted-foreground mt-2">
        Chỉ chấp nhận file .PDF — tối đa 20MB
      </p>
    </div>
  );
}