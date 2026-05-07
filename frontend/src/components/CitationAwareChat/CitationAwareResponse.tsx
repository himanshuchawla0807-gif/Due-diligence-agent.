import React, { useMemo, useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import type { Citation } from '../../types';
import { CitationPopover } from './CitationPopover';
import { ChartRenderer } from './ChartRenderer';
import { FileText, Copy, Share2, ThumbsUp, ThumbsDown, Check } from 'lucide-react';

interface CitationAwareResponseProps {
  content: string;
  citations: Citation[];
  onCitationClick: (citation: Citation) => void;
  onDocumentSelect?: (documentPath: string) => void;
}

export function CitationAwareResponse({ content, citations, onCitationClick, onDocumentSelect }: CitationAwareResponseProps) {
  // Parse citation IDs from content and create mapping
  const citationMap = useMemo(() => {
    const map = new Map<string, { number: number; citation: Citation }>();
    let citationNumber = 1;

    // Validate citations array
    if (!Array.isArray(citations)) {
      console.error('[CitationAwareResponse] citations is not an array:', citations);
      return map;
    }

    citations.forEach((citation) => {
      // Validate citation object
      if (!citation || !citation.id) {
        return;
      }

      if (!map.has(citation.id)) {
        map.set(citation.id, {
          number: citationNumber++,
          citation
        });
      }
    });

    return map;
  }, [citations]);

  // State for processed content and charts
  const [processedContent, setProcessedContent] = useState<string>('');
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);

  // Parse content and extract charts when content or citations change
  useEffect(() => {
    if (!content) {
      setProcessedContent('');
      setChartData([]);
      return;
    }

    let processed = content;
    const newChartData: any[] = [];

    // 1. Process Citations
    // Replace <c>citation_id</c> with [CIT:number] format for rendering
    processed = processed.replace(/<c>([^<>]+)<\/c>/g, (_match, citationId) => {
      const citationData = citationMap.get(citationId);
      if (citationData) {
        return `[CIT:${citationData.number}]`;
      }
      return ''; // Hide broken citations
    });

    // Also handle alternative format: <cite>...</cite>
    processed = processed.replace(/<cite>([^<>]+)<\/cite>/g, (_match, citationId) => {
      const citationData = citationMap.get(citationId);
      if (citationData) {
        return `[CIT:${citationData.number}]`;
      }
      return '';
    });

    // Handle plain text citations [1], [2] etc.
    // This is a fallback for when the backend sends plain text markers
    processed = processed.replace(/\[(\d+)\]/g, (match, numStr) => {
      const num = parseInt(numStr, 10);
      // Check if we have a citation at this index (1-based)
      // We assume the citations array order matches the numbering
      if (num > 0 && num <= citations.length) {
        return `[CIT:${num}]`;
      }
      return match;
    });

    // REMOVE COMMAS BETWEEN CITATIONS
    // Replaces "[CIT:1], [CIT:2]" or "[CIT:1],[CIT:2]" with "[CIT:1][CIT:2]"
    processed = processed.replace(/\]\s*,\s*\[/g, '][');

    // Strip "References" or "Sources" section from the end of the text
    const referencesRegex = /(?:\n|^)\s*(?:###\s*)?(?:References|Sources|Bibliography|Citations)[\s\S]*$/i;
    processed = processed.replace(referencesRegex, '');

    // Also strip lines that look like "[1] filename" at the end if they weren't caught
    const looseSourceRegex = /(?:\n|^)\s*\[\d+\]\s+.*(?:\n\s*\[\d+\]\s+.*)*$/;
    processed = processed.replace(looseSourceRegex, '');

    // 2. Parse Chart Placeholders with Position-Based Mapping
    // Matches: *Pie chart of Revenue by Region* or (Bar chart of Growth) etc.
    const placeholderRegex = /(?:\*|\[|\()\s*(Pie|Bar|Line)\s+chart\s+(?:of\s+)?(.*?)(?:\*|\]|\))/gi;
    const placeholders = [...processed.matchAll(placeholderRegex)];

    // More tolerant table regex - handles optional outer pipes and various separator formats
    // Matches standard markdown tables with or without outer pipes
    const tableRegex = /(?:^|\n)((?:\|?.+\|?[\r\n]+)+\|?[-:|\s]+\|?[\r\n]+(?:\|?.+\|?[\r\n]*)+)/g;
    const tables = [...processed.matchAll(tableRegex)];

    if (placeholders.length > 0) {
      const replacements: { index: number, length: number, replacement: string }[] = [];

      placeholders.forEach((match) => {
        const placeholderIndex = match.index!;
        const placeholderStr = match[0];
        const chartType = match[1]; // Pie, Bar, or Line
        let chartTitle = match[2].trim(); // Captured title group

        // Clean up title
        chartTitle = chartTitle.replace(/^of\s+/i, '').replace(/[:*\])]+$/, '').trim();
        if (!chartTitle) chartTitle = `${chartType} Chart`;

        // Find nearest preceding table
        let nearestTableMatch = null;
        let minDistance = Infinity;

        for (const tableMatch of tables) {
          const tableIndex = tableMatch.index!;
          // Table must start before the placeholder
          if (tableIndex < placeholderIndex) {
            const distance = placeholderIndex - tableIndex;
            if (distance < minDistance) {
              minDistance = distance;
              nearestTableMatch = tableMatch;
            }
          }
        }

        if (nearestTableMatch) {
          // Extract data from table
          const tableContent = nearestTableMatch[0];
          const rows = tableContent.trim().split('\n').filter(row => row.trim().includes('|') && !row.includes('---')); // Filter out non-row lines

          const data = rows.slice(1).map((row) => { // Skip header
            // Handle rows with or without outer pipes
            const cols = row.split('|').map(c => c.trim()).filter(c => c !== '');
            if (cols.length >= 2) {
              const name = cols[0].replace(/\*\*/g, '').trim(); // Clean name
              const valueStrRaw = cols[1];

              // STRICT VALIDATION: Must contain at least one digit
              if (!/\d/.test(valueStrRaw)) {
                return null;
              }

              // Clean value string (remove $, %, commas, etc.)
              const valueStr = valueStrRaw.replace(/[^0-9.-]/g, '');
              const value = parseFloat(valueStr);

              if (isNaN(value)) {
                return null;
              }

              return { name, value, original: valueStrRaw };
            }
            return null;
          }).filter(item => item !== null);

          if (data.length > 0) {
            newChartData.push(data);
            // Encode title in the tag: [CHART:TYPE:INDEX:TITLE_BASE64] to avoid parsing issues
            const safeTitle = chartTitle.replace(/[\[\]]/g, '');
            // Use block code syntax with 'chart' language to ensure it breaks out of paragraphs/tables
            replacements.push({
              index: placeholderIndex,
              length: placeholderStr.length,
              replacement: `\n\n\`\`\`chart\n[CHART:${chartType.toLowerCase()}:${newChartData.length - 1}:${safeTitle}]\n\`\`\`\n\n`
            });
          }
        }
      });

      // Apply replacements in reverse order to preserve indices
      replacements.sort((a, b) => b.index - a.index);

      for (const { index, length, replacement } of replacements) {
        processed = processed.substring(0, index) + replacement + processed.substring(index + length);
      }
    }

    // 3. Convert [CIT:N] to Markdown Links for Interactive Rendering
    // We convert [CIT:12] -> [12](https://citation/12)
    // We use https:// protocol to avoid ReactMarkdown sanitization stripping custom protocols
    processed = processed.replace(/\[CIT:(\d+)\]/g, '[$1](https://citation/$1)');

    setProcessedContent(processed);
    setChartData(newChartData);

  }, [content, citationMap, citations]);

  // Create grouped list of citations for display at bottom
  const groupedSources = useMemo(() => {
    const groups = new Map<string, { fileName: string; citations: { number: number; citation: Citation }[] }>();

    // Helper to add citation to group
    const addCitation = (number: number, citation: Citation) => {
      const fileName = citation.file_name || citation.relative_path || 'Unknown Document';
      if (!groups.has(fileName)) {
        groups.set(fileName, { fileName, citations: [] });
      }
      groups.get(fileName)!.citations.push({ number, citation });
    };

    if (citationMap.size > 0) {
      Array.from(citationMap.values()).forEach(({ number, citation }) => {
        addCitation(number, citation);
      });
    } else {
      citations.forEach((citation, idx) => {
        addCitation(idx + 1, citation);
      });
    }

    return Array.from(groups.values());
  }, [citationMap, citations]);

  // Handler for badge interactions
  const handleBadgeClick = React.useCallback((e: React.MouseEvent, citationNum: number) => {
    e.preventDefault(); // Prevent default link behavior
    e.stopPropagation();

    // Find citation by number
    let citationObj: Citation | null = null;
    for (const [, { number, citation }] of citationMap) {
      if (number === citationNum) {
        citationObj = citation;
        break;
      }
    }

    // Fallback
    if (!citationObj && citations[citationNum - 1]) {
      citationObj = citations[citationNum - 1];
    }

    if (citationObj) {
      // Open Popover first, then user can click to view full document
      setActiveCitation(citationObj);
    }
  }, [citationMap, citations]);

  // Generate consistent pastel color based on citation number
  const getBadgeColor = (num: number) => {
    const colors = [
      { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200', hoverBg: 'hover:bg-blue-200', hoverBorder: 'hover:border-blue-300' },
      { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-200', hoverBg: 'hover:bg-purple-200', hoverBorder: 'hover:border-purple-300' },
      { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200', hoverBg: 'hover:bg-green-200', hoverBorder: 'hover:border-green-300' },
      { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', hoverBg: 'hover:bg-red-200', hoverBorder: 'hover:border-red-300' },
      { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', hoverBg: 'hover:bg-amber-200', hoverBorder: 'hover:border-amber-300' },
      { bg: 'bg-indigo-100', text: 'text-indigo-700', border: 'border-indigo-200', hoverBg: 'hover:bg-indigo-200', hoverBorder: 'hover:border-indigo-300' },
      { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-200', hoverBg: 'hover:bg-teal-200', hoverBorder: 'hover:border-teal-300' },
      { bg: 'bg-rose-100', text: 'text-rose-700', border: 'border-rose-200', hoverBg: 'hover:bg-rose-200', hoverBorder: 'hover:border-rose-300' },
    ];
    return colors[(num - 1) % colors.length];
  };

  // Custom components for ReactMarkdown (ChatGPT-style)
  const components = {
    // Hijack links to render citations
    a: ({ href, children }: any) => {
      // Check for our custom citation protocol (using https to bypass sanitization)
      if (href && (href.startsWith('citation:') || href.startsWith('https://citation/'))) {
        const citationNumStr = href.replace('https://citation/', '').replace('citation:', '');
        const citationNum = parseInt(citationNumStr, 10);
        const color = getBadgeColor(citationNum);

        return (
          <sup
            className="inline-flex items-center justify-center ml-0.5 mr-0.5 align-top group/citation relative cursor-pointer select-none"
            style={{ top: '-0.2em' }}
            onClick={(e) => handleBadgeClick(e, citationNum)}
          >
            <span
              className={`flex items-center justify-center w-4 h-4 rounded-md ${color.bg} border ${color.border} text-[9px] font-bold ${color.text} shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:scale-110 ${color.hoverBg} ${color.hoverBorder} hover:shadow-md transition-all duration-200 ease-out transform-gpu`}
              style={{ fontFamily: 'SF Pro Text, -apple-system, BlinkMacSystemFont, sans-serif' }}
            >
              {children}
            </span>
          </sup>
        );
      }
      return <a href={href} className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>;
    },
    p: ({ children }: any) => <p className="mb-5 leading-7 text-base text-gray-900 font-medium">{children}</p>,
    li: ({ children }: any) => (
      <li className="mb-2 pl-0 text-base leading-7 text-gray-900 font-medium list-none">
        <div className="flex items-start gap-3">
          <span className="w-1.5 h-1.5 bg-gray-800 rounded-full mt-2.5 flex-shrink-0"></span>
          <span className="flex-1 min-w-0">{children}</span>
        </div>
      </li>
    ),
    ul: ({ children }: any) => (
      <ul className="space-y-1 my-4 pl-0 list-none">{children}</ul>
    ),
    ol: ({ children }: any) => (
      <ol className="my-5 space-y-3 pl-6 list-decimal">{children}</ol>
    ),
    strong: ({ children }: any) => (
      <strong className="font-semibold text-gray-900">{children}</strong>
    ),
    h1: ({ children }: any) => (
      <h1 className="text-4xl font-bold text-gray-900 mt-8 mb-6 leading-tight tracking-tight border-b border-gray-100 pb-4">{children}</h1>
    ),
    h2: ({ children }: any) => (
      <h2 className="text-2xl font-bold text-gray-800 mt-10 mb-4 tracking-tight flex items-center gap-2">
        <span className="w-1.5 h-6 bg-blue-600 rounded-full"></span>
        {children}
      </h2>
    ),
    h3: ({ children }: any) => (
      <h3 className="text-xl font-semibold text-gray-800 mt-8 mb-3 tracking-tight">{children}</h3>
    ),
    table: ({ children }: any) => (
      <div className="overflow-x-auto my-8 rounded-xl border border-gray-200 shadow-md bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-gray-50">
        {children}
      </thead>
    ),
    tbody: ({ children }: any) => (
      <tbody className="divide-y divide-gray-200 bg-white">
        {children}
      </tbody>
    ),
    tr: ({ children }: any) => (
      <tr className="hover:bg-gray-50/50 transition-colors duration-150">
        {children}
      </tr>
    ),
    th: ({ children }: any) => (
      <th className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider bg-gray-50 border-b border-gray-200">
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="px-6 py-4 whitespace-normal text-sm text-gray-700 leading-relaxed">
        {children}
      </td>
    ),
    pre: ({ children }: any) => <div className="not-prose p-0 m-0 bg-transparent">{children}</div>,
    code: ({ node, inline, className, children }: any) => {
      // Normalize children to string
      const content = Array.isArray(children)
        ? children.map((c: any) => String(c)).join('')
        : String(children);

      // Check if this is a chart block (either by class or content)
      const isChartBlock = !inline && (className === 'language-chart' || content.trim().startsWith('[CHART:'));

      if (isChartBlock || content.startsWith('[CHART:')) {
        // Match [CHART:type:index:title]
        const match = content.match(/\[CHART:(\w+):(\d+)(?::(.*?))?\]/);
        if (match) {
          const [, type, dataIndex, title] = match;
          const index = parseInt(dataIndex, 10);

          if (chartData[index]) {
            try {
              // Ensure full width container for the chart
              // Using min-h-[400px] to ensure it's "bigger in size" as requested
              return (
                <div className="w-full block my-8 not-prose">
                  <ChartRenderer
                    chartType={type}
                    data={chartData[index]}
                    title={title || `${type.charAt(0).toUpperCase() + type.slice(1)} Chart`}
                  />
                </div>
              );
            } catch (error) {
              console.error(`[CitationAwareResponse] Error rendering chart:`, error);
              return <div className="text-red-500 p-2 border border-red-300 rounded">Chart rendering failed</div>;
            }
          } else {
            console.error(`[CitationAwareResponse] Chart data missing for index ${index}`);
            return <div className="text-amber-500 p-2 border border-amber-300 rounded">Chart data not found</div>;
          }
        }
      }

      // Check if content looks like a filename (e.g., ends with extension, no spaces usually, or specific format)
      // Regex for common extensions or file-like patterns
      const isFilename = /\.(pdf|md|txt|docx|csv|xlsx|json|py|js|ts|tsx|html|css)$/i.test(content.trim()) ||
        (content.includes('_') && content.includes('.'));

      if (isFilename) {
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-gray-200 text-gray-700 font-sans text-[13px] font-medium shadow-sm align-middle mx-0.5">
            <FileText className="w-3.5 h-3.5 text-gray-500" />
            {content}
          </span>
        );
      }

      return <code className="bg-gray-100 rounded-md px-1.5 py-0.5 text-[14px] font-medium font-mono text-gray-800 border border-gray-200">{children}</code>;
    },
  };

  // Clean text for copying (remove markdown, citations, etc.)
  const getCleanTextForCopy = useCallback(() => {
    let text = content;
    // Remove citation tags
    text = text.replace(/<c>[^<>]+<\/c>/g, '');
    text = text.replace(/<cite>[^<>]+<\/cite>/g, '');
    text = text.replace(/\[\d+\]/g, '');
    // Remove markdown formatting
    text = text.replace(/#{1,6}\s*/g, '');
    text = text.replace(/\*\*([^*]+)\*\*/g, '$1');
    text = text.replace(/\*([^*]+)\*/g, '$1');
    text = text.replace(/<br\s*\/?>/gi, '\n');
    // Remove table formatting
    text = text.replace(/\|/g, ' ');
    text = text.replace(/---+/g, '');
    // Clean up extra whitespace
    text = text.replace(/\n{3,}/g, '\n\n');
    text = text.trim();
    return text;
  }, [content]);

  // Copy and feedback state
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(getCleanTextForCopy());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [getCleanTextForCopy]);

  const handleShare = useCallback(async () => {
    const text = getCleanTextForCopy();
    if (navigator.share) {
      try {
        await navigator.share({ text });
      } catch (err) {
        // User cancelled or other error
      }
    } else {
      // Fallback to copy
      handleCopy();
    }
  }, [getCleanTextForCopy, handleCopy]);

  const handleFeedback = useCallback((type: 'up' | 'down') => {
    setFeedback(feedback === type ? null : type);
    // TODO: Send feedback to backend
    console.log('Feedback:', type);
  }, [feedback]);

  return (
    <div className="citation-aware-response relative group bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden transition-all duration-300 hover:shadow-md">
      {/* Response content with markdown rendering - ChatGPT style */}
      <div className="max-w-none text-gray-800 prose prose-p:leading-7 prose-headings:font-bold prose-a:text-blue-600 p-6 text-[16px] leading-7" style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={components}>
          {processedContent}
        </ReactMarkdown>
      </div>

      {/* Action buttons - Copy, Share, Feedback */}
      <div className="flex items-center gap-2 px-6 py-3 border-t border-gray-100 bg-gray-50/50">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
          title="Copy to clipboard"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
          title="Share"
        >
          <Share2 className="w-3.5 h-3.5" />
          Share
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleFeedback('up')}
            className={`p-1.5 rounded-lg transition-all ${feedback === 'up' ? 'bg-green-100 text-green-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
            title="Good response"
          >
            <ThumbsUp className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleFeedback('down')}
            className={`p-1.5 rounded-lg transition-all ${feedback === 'down' ? 'bg-red-100 text-red-600' : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'}`}
            title="Poor response"
          >
            <ThumbsDown className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Citations list at bottom - Grouped by File */}
      {groupedSources.length > 0 && (
        <div className="bg-gray-50/50 px-6 py-6 border-t border-gray-100 backdrop-blur-sm">
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-5 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-600"></span>
            Referenced Documents
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {groupedSources.map((group, groupIdx) => (
              <div key={groupIdx} className="flex flex-col gap-3 bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-all duration-200 group/card">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 rounded-full bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-500 shadow-sm group-hover/card:scale-110 transition-transform duration-200">
                      <FileText className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="text-sm font-semibold text-gray-900 truncate leading-tight mb-1" title={group.fileName}>
                      {group.fileName}
                    </div>
                    <div className="text-xs text-gray-500 font-medium">
                      {group.citations.length} citation{group.citations.length !== 1 ? 's' : ''}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5 pl-[3.25rem]">
                  {group.citations.map(({ number, citation }) => {
                    const color = getBadgeColor(number);
                    return (
                      <div
                        key={number}
                        className={`cursor-pointer transition-transform hover:scale-105 active:scale-95`}
                        onClick={() => onCitationClick(citation)}
                      >
                        <span
                          className={`inline-flex items-center justify-center h-5 px-2 rounded-md ${color.bg} border ${color.border} ${color.text} text-[10px] font-bold shadow-sm hover:shadow-md transition-all`}
                          style={{ fontFamily: 'SF Pro Text, -apple-system, BlinkMacSystemFont, sans-serif' }}
                        >
                          {number}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Citation Popover */}
      <CitationPopover
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
        onOpenDocument={onCitationClick}
        onDocumentSelect={onDocumentSelect}
      />
    </div>
  );
}
