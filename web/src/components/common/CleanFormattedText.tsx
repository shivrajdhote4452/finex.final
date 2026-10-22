import React from 'react';

interface CleanFormattedTextProps {
  text: string;
  fontSize?: string;
  compact?: boolean;
}

/**
 * Parses inline markdown:
 * - `code`
 * - ***bold italic***
 * - **bold** or __bold__
 * - *italic* or _italic_
 * - Converts raw asterisks and markdown symbols into clean styled typography
 */
export const renderInlineText = (text: string): React.ReactNode => {
  if (!text) return null;

  // Pattern matches:
  // 1. Markdown link: [label](url)
  // 2. Inline code: `code`
  // 3. Bold italic: ***text***
  // 4. Bold: **text** or __text__
  // 5. Italic: *text* or _text_
  const tokenRegex = /(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, i) => {
    if (!part) return null;

    // Markdown Link: [label](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a
          key={i}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: '#F29A60',
            textDecoration: 'underline',
            textUnderlineOffset: '2px',
          }}
        >
          {linkMatch[1]}
        </a>
      );
    }

    // Inline code: `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={i}
          style={{
            backgroundColor: 'rgba(255, 255, 255, 0.08)',
            color: '#F29A60',
            padding: '1px 5px',
            borderRadius: '4px',
            fontSize: '0.88em',
            fontFamily: 'SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold + Italic: ***text***
    if (part.startsWith('***') && part.endsWith('***') && part.length >= 6) {
      return (
        <strong key={i} style={{ color: '#FFFFFF', fontWeight: 700, fontStyle: 'italic' }}>
          {part.slice(3, -3)}
        </strong>
      );
    }

    // Bold: **text** or __text__
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      return (
        <strong key={i} style={{ color: '#FFFFFF', fontWeight: 600 }}>
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic: *text* or _text_
    if (
      (part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length >= 2)
    ) {
      return (
        <em key={i} style={{ color: '#E5E5EA', fontStyle: 'italic' }}>
          {part.slice(1, -1)}
        </em>
      );
    }

    // Plain text: remove any stray unclosed markdown asterisks/underscores for visual cleanliness
    const cleaned = part.replace(/\*\*/g, '').replace(/__/g, '');
    return cleaned;
  });
};

type ContentBlock =
  | { type: 'heading'; level: number; text: string }
  | { type: 'step-heading'; number: string; title: string }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'callout'; tag: string; content: string }
  | { type: 'bullet'; text: string }
  | { type: 'numbered-list'; number: string; text: string }
  | { type: 'divider' }
  | { type: 'paragraph'; text: string }
  | { type: 'empty' };

export const CleanFormattedText: React.FC<CleanFormattedTextProps> = ({
  text,
  fontSize = '13.5px',
  compact = false,
}) => {
  if (!text) return null;

  // 1. Group raw text lines into structured blocks
  const lines = text.split('\n');
  const blocks: ContentBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // Check if this is the start of a Markdown Table (consecutive lines with '|')
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 1) {
        const parseRow = (line: string): string[] => {
          return line
            .split('|')
            .slice(1, -1)
            .map((c) => c.trim());
        };

        const headers = parseRow(tableLines[0]);
        const rows: string[][] = [];

        for (let t = 1; t < tableLines.length; t++) {
          const cells = parseRow(tableLines[t]);
          // Skip separator rows like |---|---|
          if (cells.every((c) => /^[:\s-]+$/.test(c))) {
            continue;
          }
          rows.push(cells);
        }

        blocks.push({ type: 'table', headers, rows });
        continue;
      }
    }

    // Horizontal Rule: --- or *** or ___ or - - -
    if (/^([-*_]\s*){3,}$/.test(trimmed)) {
      blocks.push({ type: 'divider' });
      i++;
      continue;
    }

    // Markdown Headers: # , ## , ### , ####
    if (trimmed.startsWith('#### ')) {
      blocks.push({ type: 'heading', level: 4, text: trimmed.replace(/^####\s+/, '') });
      i++;
      continue;
    }
    if (trimmed.startsWith('### ')) {
      blocks.push({ type: 'heading', level: 3, text: trimmed.replace(/^###\s+/, '') });
      i++;
      continue;
    }
    if (trimmed.startsWith('## ')) {
      blocks.push({ type: 'heading', level: 2, text: trimmed.replace(/^##\s+/, '') });
      i++;
      continue;
    }
    if (trimmed.startsWith('# ')) {
      blocks.push({ type: 'heading', level: 1, text: trimmed.replace(/^#\s+/, '') });
      i++;
      continue;
    }

    // Standalone Bold Section Heading: e.g. "**How to Approach What Stocks Might Be Interesting Today?**"
    const boldHeaderMatch = trimmed.match(/^\*\*([^*]+)\*\*$/);
    if (boldHeaderMatch && boldHeaderMatch[1].length < 100 && !trimmed.endsWith('.')) {
      blocks.push({
        type: 'heading',
        level: 3,
        text: boldHeaderMatch[1],
      });
      i++;
      continue;
    }

    // Callout / Highlighted Example Box: e.g. "**Important Note:**", "**Warning:**", "> ...", "Note:", "Important:"
    const calloutHeaderMatch =
      trimmed.match(/^(\*\*|>|\b)(Important Note|Important|Note|Warning|Disclaimer|Risk Disclosure|Caution|Notice|Tip|Key Takeaway|Takeaway|Summary|Example):?(\*\*|)?\s*(.*)$/i) ||
      (trimmed.startsWith('> ') ? [trimmed, '', 'Note', '', trimmed.replace(/^>\s*/, '')] : null);

    if (calloutHeaderMatch) {
      const tag = (calloutHeaderMatch[2] || 'Note').replace(/\*\*/g, '').trim();
      let content = (calloutHeaderMatch[4] || '').trim();

      // If callout title was on its own line (e.g. "**Important Note:**\n\nI'm not permitted..."), grab following paragraph lines
      if (!content) {
        let nextIdx = i + 1;
        while (nextIdx < lines.length && !lines[nextIdx].trim()) {
          nextIdx++;
        }
        if (
          nextIdx < lines.length &&
          !lines[nextIdx].trim().startsWith('#') &&
          !lines[nextIdx].trim().startsWith('|') &&
          !lines[nextIdx].trim().startsWith('-') &&
          !lines[nextIdx].trim().startsWith('*') &&
          !lines[nextIdx].trim().startsWith('•') &&
          !/^\d+[\.)]/.test(lines[nextIdx].trim()) &&
          !/^[-*_]{3,}$/.test(lines[nextIdx].trim())
        ) {
          content = lines[nextIdx].trim();
          i = nextIdx;
        }
      }

      blocks.push({
        type: 'callout',
        tag: tag.toUpperCase(),
        content: content || tag,
      });
      i++;
      continue;
    }

    // Numbered List / Major Step Heading: e.g. "1. **Start with a Market-wide View**" or "1. Simple item"
    const numMatch = trimmed.match(/^(\d+)[\.)]\s+(.*)$/);
    if (numMatch) {
      const num = numMatch[1];
      const rest = numMatch[2].trim();

      // Check if this is a major section title (e.g., "1. **Start with a Market-wide View**" or short title without ending punctuation)
      const isHeaderLike =
        (rest.startsWith('**') && rest.endsWith('**')) ||
        (rest.length < 80 && !rest.endsWith('.') && !rest.includes(': '));

      if (isHeaderLike) {
        blocks.push({
          type: 'step-heading',
          number: num,
          title: rest.replace(/^\*\*|\*\*$/g, '').replace(/\*\*/g, ''),
        });
      } else {
        blocks.push({
          type: 'numbered-list',
          number: num,
          text: rest,
        });
      }
      i++;
      continue;
    }

    // Unordered Bullet List: • item, - item, * item, + item, · item, ▪ item
    const bulletMatch = trimmed.match(/^([•\-\*\+·▪▫])\s+(.*)$/);
    if (bulletMatch) {
      blocks.push({ type: 'bullet', text: bulletMatch[2] });
      i++;
      continue;
    }

    // Empty spacing line
    if (!trimmed) {
      blocks.push({ type: 'empty' });
      i++;
      continue;
    }

    // Standard Paragraph
    blocks.push({ type: 'paragraph', text: rawLine });
    i++;
  }

  // 2. Render structured blocks with high-polish dark theme typography
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: compact ? '4px' : '6px',
        fontSize,
        lineHeight: 1.55,
        color: '#D4D4D8',
      }}
    >
      {blocks.map((block, idx) => {
        switch (block.type) {
          case 'heading': {
            const size =
              block.level === 1
                ? compact ? '16px' : '18px'
                : block.level === 2
                ? compact ? '14.5px' : '16px'
                : compact ? '13px' : '14.5px';
            const color = block.level <= 2 ? '#FFFFFF' : '#F29A60';
            return (
              <div
                key={idx}
                style={{
                  fontSize: size,
                  fontWeight: 700,
                  color,
                  margin: compact ? '6px 0 2px 0' : '10px 0 3px 0',
                  letterSpacing: '-0.01em',
                }}
              >
                {renderInlineText(block.text)}
              </div>
            );
          }

          case 'step-heading': {
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  margin: compact ? '8px 0 3px 0' : '12px 0 4px 0',
                }}
              >
                <span
                  style={{
                    backgroundColor: 'rgba(242, 154, 96, 0.18)',
                    color: '#F29A60',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '4px',
                    border: '1px solid rgba(242, 154, 96, 0.3)',
                  }}
                >
                  {block.number}
                </span>
                <span
                  style={{
                    fontSize: compact ? '13.5px' : '15px',
                    fontWeight: 700,
                    color: '#FFFFFF',
                    letterSpacing: '-0.01em',
                  }}
                >
                  {renderInlineText(block.title)}
                </span>
              </div>
            );
          }

          case 'table': {
            return (
              <div
                key={idx}
                style={{
                  margin: compact ? '6px 0' : '10px 0',
                  borderRadius: '6px',
                  border: '1px solid #232733',
                  backgroundColor: '#0F1117',
                  overflow: 'hidden',
                }}
              >
                <div style={{ overflowX: 'auto', width: '100%' }}>
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: compact ? '11.5px' : '12.5px',
                      textAlign: 'left',
                    }}
                  >
                    {block.headers.length > 0 && (
                      <thead>
                        <tr
                          style={{
                            backgroundColor: '#181B24',
                            borderBottom: '1px solid #282C3A',
                          }}
                        >
                          {block.headers.map((h, hIdx) => (
                            <th
                              key={hIdx}
                              style={{
                                padding: compact ? '6px 10px' : '8px 12px',
                                fontWeight: 600,
                                color: '#FFFFFF',
                                letterSpacing: '0.02em',
                                borderRight: hIdx < block.headers.length - 1 ? '1px solid #232733' : 'none',
                              }}
                            >
                              {renderInlineText(h)}
                            </th>
                          ))}
                        </tr>
                      </thead>
                    )}
                    <tbody>
                      {block.rows.map((row, rIdx) => (
                        <tr
                          key={rIdx}
                          style={{
                            backgroundColor: rIdx % 2 === 0 ? 'rgba(255, 255, 255, 0.015)' : 'transparent',
                            borderBottom: rIdx < block.rows.length - 1 ? '1px solid #1C202B' : 'none',
                          }}
                        >
                          {row.map((cell, cIdx) => (
                            <td
                              key={cIdx}
                              style={{
                                padding: compact ? '6px 10px' : '8px 12px',
                                color: cIdx === 0 ? '#FFFFFF' : '#D1D5DB',
                                verticalAlign: 'top',
                                lineHeight: '1.45',
                                borderRight: cIdx < row.length - 1 ? '1px solid #1C202B' : 'none',
                              }}
                            >
                              {renderInlineText(cell)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          }

          case 'callout': {
            return (
              <div
                key={idx}
                style={{
                  margin: compact ? '6px 0' : '9px 0',
                  padding: compact ? '7px 10px' : '9px 13px',
                  backgroundColor: 'rgba(242, 154, 96, 0.06)',
                  borderLeft: '3px solid #F29A60',
                  borderRadius: '0 6px 6px 0',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '3px',
                }}
              >
                {block.tag && (
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: '#F29A60',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <span>
                      {block.tag.includes('WARNING') || block.tag.includes('CAUTION') || block.tag.includes('RISK')
                        ? '⚠️'
                        : block.tag.includes('NOTE') || block.tag.includes('IMPORTANT') || block.tag.includes('NOTICE')
                        ? '📌'
                        : block.tag.includes('TIP') || block.tag.includes('INSIGHT')
                        ? '💡'
                        : block.tag.includes('SUMMARY') || block.tag.includes('TAKEAWAY')
                        ? '🎯'
                        : '💡'}
                    </span>
                    <span>{block.tag}</span>
                  </div>
                )}
                <div style={{ fontSize: compact ? '12px' : '13px', color: '#E5E5EA', lineHeight: '1.5' }}>
                  {renderInlineText(block.content)}
                </div>
              </div>
            );
          }

          case 'bullet': {
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '8px',
                  paddingLeft: '4px',
                  margin: '2px 0',
                }}
              >
                <span
                  style={{
                    color: '#F29A60',
                    fontSize: '13px',
                    lineHeight: '1.4',
                    userSelect: 'none',
                  }}
                >
                  •
                </span>
                <span style={{ flex: 1, color: '#D4D4D8' }}>
                  {renderInlineText(block.text)}
                </span>
              </div>
            );
          }

          case 'numbered-list': {
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '8px',
                  paddingLeft: '4px',
                  margin: '2px 0',
                }}
              >
                <span
                  style={{
                    color: '#F29A60',
                    fontSize: '11.5px',
                    fontWeight: 700,
                    minWidth: '16px',
                    userSelect: 'none',
                  }}
                >
                  {block.number}.
                </span>
                <span style={{ flex: 1, color: '#D4D4D8' }}>
                  {renderInlineText(block.text)}
                </span>
              </div>
            );
          }

          case 'divider': {
            return (
              <hr
                key={idx}
                style={{
                  border: 'none',
                  borderTop: '1px solid #232733',
                  margin: compact ? '6px 0' : '10px 0',
                }}
              />
            );
          }

          case 'empty': {
            return <div key={idx} style={{ height: compact ? '2px' : '4px' }} />;
          }

          case 'paragraph': {
            return (
              <p
                key={idx}
                style={{
                  margin: 0,
                  color: '#D4D4D8',
                }}
              >
                {renderInlineText(block.text)}
              </p>
            );
          }

          default:
            return null;
        }
      })}
    </div>
  );
};
