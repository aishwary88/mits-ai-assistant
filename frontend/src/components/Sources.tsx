import { useState } from 'react';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import type { Source } from '../types/chat';
import { sourceFilename } from '../api/chat';

interface Props {
  sources?: Source[];
}

export function Sources({ sources }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  // Deduplicate by filename
  const seen = new Set<string>();
  const unique = sources.filter((s) => {
    const name = sourceFilename(s.title);
    if (seen.has(name)) return false;
    seen.add(name);
    return true;
  });

  return (
    <div className="mt-2.5">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-text-muted hover:text-text transition-colors"
        aria-expanded={expanded}
      >
        <FileText className="w-3.5 h-3.5" />
        <span>
          {unique.length} source{unique.length > 1 ? 's' : ''}
        </span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5">
          {unique.map((src, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-md border border-border bg-surface-hover px-2.5 py-1.5"
            >
              <FileText className="w-3.5 h-3.5 mt-0.5 shrink-0 text-text-muted" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium text-text">
                  {sourceFilename(src.title)}
                </div>
                <div className="flex items-center gap-2 text-[0.7rem] text-text-muted">
                  {src.type && <span>{src.type}</span>}
                  {src.page > 0 && <span>· p.{src.page}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
