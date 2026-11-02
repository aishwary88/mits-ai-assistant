import { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({
  breaks: true,
  gfm: true,
});

// Add target="_blank" rel="noopener" to all links after sanitization.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

// Wrap <table> elements in a scroll container div.
function wrapTables(html: string): string {
  return html
    .replace(/<table>/g, '<div class="md-table-wrap"><table>')
    .replace(/<\/table>/g, '</table></div>');
}

interface Props {
  content: string;
}

export function MarkdownRenderer({ content }: Props) {
  const html = useMemo(() => {
    const raw = marked.parse(content, { async: false }) as string;
    const wrapped = wrapTables(raw);
    return DOMPurify.sanitize(wrapped, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'ul', 'ol', 'li',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'hr', 'a', 'span', 'div',
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
    });
  }, [content]);

  return <div className="md-content" dangerouslySetInnerHTML={{ __html: html }} />;
}
