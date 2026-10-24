import { Database } from 'lucide-react';
import { SOURCE_CONFIG } from './types';

export function SourceIcon({ source }: { source: string }) {
  const config = SOURCE_CONFIG[source.toLowerCase()] ?? SOURCE_CONFIG.crossref;
  return <Database className={`h-4 w-4 ${config.color}`} />;
}
