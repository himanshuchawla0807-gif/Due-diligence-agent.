import React, { useState, useEffect, useRef, useMemo } from 'react';
import { API_BASE_URL } from '@/config';
import { X, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as XLSX from 'xlsx';
import type { Citation } from '../../types';
import { PDFHighlighterViewer } from './PDFHighlighterViewer';

interface DocumentViewerPanelProps {
  sessionId: string;
  fileName: string;
  citation: Citation;
  onClose: () => void;
}

class GlobalErrorBoundary extends React.Component<{ children: React.ReactNode, onClose: () => void }, { hasError: boolean, error: Error | null }> {
  constructor(props: { children: React.ReactNode, onClose: () => void }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("DocumentViewerPanel crashed:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex flex-col bg-white">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white z-10">
            <h3 className="text-lg font-medium text-red-600">Viewer Error</h3>
            <button onClick={this.props.onClose} className="p-2 hover:bg-gray-100 rounded-full text-gray-400">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="bg-red-50 p-6 rounded-xl max-w-md">
              <h3 className="text-lg font-medium text-red-900 mb-2">Something went wrong</h3>
              <p className="text-red-700 mb-4">The document viewer encountered an error.</p>
              <pre className="text-xs text-left bg-white p-4 rounded border border-red-100 overflow-auto max-h-40 text-red-800">
                {this.state.error?.message || "Unknown error"}
              </pre>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export function DocumentViewerPanel({ sessionId, fileName, citation, onClose }: DocumentViewerPanelProps) {
  return (
    <GlobalErrorBoundary onClose={onClose}>
      <DocumentViewerPanelContent sessionId={sessionId} fileName={fileName} citation={citation} onClose={onClose} />
    </GlobalErrorBoundary>
  );
}

function DocumentViewerPanelContent({ sessionId, fileName, citation, onClose }: DocumentViewerPanelProps) {
  const [loading, setLoading] = useState(true);
  const [fileContent, setFileContent] = useState<string>('');
  const [excelData, setExcelData] = useState<Array<{ sheetName: string, data: any[][] }>>([]);
  const [activeSheet, setActiveSheet] = useState<number>(0);
  const [fileType, setFileType] = useState<'pdf' | 'markdown' | 'code' | 'text' | 'excel'>('pdf');
  const [showReferencedContent, setShowReferencedContent] = useState(true);
  const highlightRef = useRef<HTMLElement>(null);

  // Memoize markdown components to avoid hook violation
  const components = useMemo(() => ({
    p: (props: any) => <HighlightRenderer {...props} as="p" className="mb-4 leading-relaxed" citation={citation} highlightRef={highlightRef} />,
    li: (props: any) => <HighlightRenderer {...props} as="li" className="my-1" citation={citation} highlightRef={highlightRef} />,
    blockquote: (props: any) => <HighlightRenderer {...props} as="blockquote" className="border-l-4 border-gray-200 pl-4 italic my-4" citation={citation} highlightRef={highlightRef} />,
    h1: (props: any) => <HighlightRenderer {...props} as="h1" className="text-3xl font-bold mb-4 mt-8" citation={citation} highlightRef={highlightRef} />,
    h2: (props: any) => <HighlightRenderer {...props} as="h2" className="text-2xl font-bold mb-3 mt-6" citation={citation} highlightRef={highlightRef} />,
    h3: (props: any) => <HighlightRenderer {...props} as="h3" className="text-xl font-bold mb-3 mt-6" citation={citation} highlightRef={highlightRef} />,
    h4: (props: any) => <HighlightRenderer {...props} as="h4" className="text-lg font-bold mb-2 mt-4" citation={citation} highlightRef={highlightRef} />,
    h5: (props: any) => <HighlightRenderer {...props} as="h5" className="text-base font-bold mb-2 mt-4" citation={citation} highlightRef={highlightRef} />,
    h6: (props: any) => <HighlightRenderer {...props} as="h6" className="text-sm font-bold mb-2 mt-4" citation={citation} highlightRef={highlightRef} />,
  }), [citation]);

  // Normalize file path to handle Windows paths
  const normalizedFileName = fileName.replace(/\\/g, '/');

  // Construct document URL - ensure we handle nested paths correctly
  // We use the normalized path and encode each segment to handle spaces/special chars
  const baseUrl = `${API_BASE_URL}/api/document/${sessionId}/${normalizedFileName.split('/').map(encodeURIComponent).join('/')}`;

  // ✅ AUTH: Get user_id from URL
  let userId = new URLSearchParams(window.location.search).get('user');
  const documentUrl = userId ? `${baseUrl}?user_id=${userId}` : baseUrl;

  // Determine file type
  useEffect(() => {
    const ext = normalizedFileName.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') {
      setFileType('pdf');
    } else if (ext === 'md' || ext === 'markdown') {
      setFileType('markdown');
    } else if (ext === 'py' || ext === 'js' || ext === 'ts' || ext === 'tsx' || ext === 'jsx' || ext === 'json') {
      setFileType('code');
    } else if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') {
      setFileType('excel');
    } else {
      setFileType('text');
    }
  }, [normalizedFileName]);

  // Load non-PDF content
  useEffect(() => {
    if (!normalizedFileName) {
      setLoading(false);
      return;
    }

    if (fileType === 'excel') {
      // Load Excel files as binary
      setLoading(true);
      fetch(documentUrl)
        .then(res => {
          if (!res.ok) throw new Error(`Failed to load document: ${res.statusText}`);
          return res.arrayBuffer();
        })
        .then(buffer => {
          const workbook = XLSX.read(buffer, { type: 'array' });
          const sheets: Array<{ sheetName: string, data: any[][] }> = [];

          workbook.SheetNames.forEach(sheetName => {
            const worksheet = workbook.Sheets[sheetName];
            const data = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
            sheets.push({ sheetName, data: data as any[][] });
          });

          setExcelData(sheets);
          setLoading(false);
        })
        .catch(err => {
          console.error('Failed to load Excel document:', err);
          setFileContent(`Error loading document: ${err.message}`);
          setLoading(false);
        });
    } else if (fileType !== 'pdf') {
      // Load text-based files
      setLoading(true);
      fetch(documentUrl)
        .then(res => {
          if (!res.ok) throw new Error(`Failed to load document: ${res.statusText}`);
          return res.text();
        })
        .then(content => {
          setFileContent(content);
          setLoading(false);
        })
        .catch(err => {
          console.error('Failed to load document:', err);
          setFileContent(`Error loading document: ${err.message}`);
          setLoading(false);
        });
    } else {
      // PDF loading is handled by PDFHighlighterViewer, but we can check if file exists
      setLoading(false);
    }
  }, [documentUrl, fileType, normalizedFileName]);

  // Scroll to highlighted section
  // Scroll to highlighted section
  useEffect(() => {
    if (citation.text_snippet) {
      // console.log('Attempting to scroll to citation:', citation.text_snippet);
      setTimeout(() => {
        if (highlightRef.current) {
          // console.log('Found highlight ref, scrolling...');
          highlightRef.current.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });
          // Add a temporary flash effect
          highlightRef.current.classList.add('ring-4', 'ring-yellow-400', 'ring-opacity-50');
          setTimeout(() => highlightRef.current?.classList.remove('ring-4', 'ring-yellow-400', 'ring-opacity-50'), 2000);
        } else {
          // console.warn('Highlight ref not found for citation');
        }
      }, 100);
    }
  }, [citation, fileContent]);



  const getFileIcon = () => {
    return <FileText className="w-5 h-5 text-blue-600" />;
  };

  // Helper component for highlighting
  const HighlightRenderer = ({ node, children, as: Component = 'p', className = '', citation, highlightRef, ...props }: any) => {
    const getText = (nodes: any): string => {
      if (!nodes) return '';
      if (typeof nodes === 'string') return nodes;
      if (Array.isArray(nodes)) return nodes.map(getText).join('');
      if (nodes?.props?.children) return getText(nodes.props.children);
      return '';
    };

    const text = getText(children);

    const calculateMatchScore = (source: string, target: string) => {
      if (!source || !target) return 0;
      // Strip XML tags and trailing ellipsis from source snippet
      let cleanSource = source.replace(/<[^>]+>/g, '');
      if (cleanSource.endsWith('...')) cleanSource = cleanSource.slice(0, -3);
      cleanSource = cleanSource.trim();

      if (!cleanSource) return 0;

      // Exact substring match check (case-insensitive) - High confidence
      if (target.toLowerCase().includes(cleanSource.toLowerCase())) return 1.0;

      const normalize = (s: string) => s.toLowerCase().replace(/[^\w\s]/g, '').split(/\s+/).filter(w => w.length >= 2);
      const sourceWords = normalize(cleanSource);
      const targetWords = new Set(normalize(target));

      if (sourceWords.length === 0 || targetWords.size === 0) return 0;

      let matches = 0;
      sourceWords.forEach(w => { if (targetWords.has(w)) matches++; });

      return matches / sourceWords.length;
    };

    const snippet = citation.text_snippet || '';
    const matchScore = calculateMatchScore(snippet, text);
    const isMatch = matchScore > 0.3;

    // Only attach ref if it's a match AND the ref hasn't been attached yet (or we want to scroll to the first match)
    // Since we render many components, we need to be careful. 
    // Ideally, we'd use a callback ref or check if we are the "best" match.
    // For now, we'll attach to any match, but the scroll logic uses the current value of the ref.

    return (
      <Component
        {...props}
        ref={isMatch ? (highlightRef as any) : null}
        className={`${className} ${isMatch ? "bg-yellow-100/80 border-l-4 border-yellow-500 pl-4 py-2 rounded shadow-sm transition-all duration-500" : ""}`}
      >
        {children}
      </Component>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
            <div>Loading document...</div>
          </div>
        </div>
      );
    }

    if (fileType === 'pdf') {
      return (
        <PDFHighlighterViewer
          sessionId={sessionId}
          fileName={normalizedFileName}
          citation={citation}
          onClose={onClose}
        />
      );
    }

    if (fileType === 'markdown') {
      // Enhanced Markdown rendering with highlighting
      return (
        <div className="prose prose-lg max-w-none p-12 text-gray-800 bg-white">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={components}
          >
            {fileContent}
          </ReactMarkdown>
        </div>
      );
    }

    if (fileType === 'code') {
      const lines = fileContent.split('\n');
      return (
        <div className="p-8 font-mono text-sm bg-white overflow-x-auto">
          {lines.map((line, idx) => {
            // Fuzzy match: check if line contains a significant part of the snippet
            const snippetPart = citation.text_snippet ? citation.text_snippet.substring(0, 30) : '';
            const isHighlighted = snippetPart && line.includes(snippetPart);

            return (
              <div
                key={idx}
                ref={isHighlighted ? (highlightRef as any) : null}
                className={`flex ${isHighlighted ? 'bg-blue-50 border-l-2 border-blue-500' : ''}`}
              >
                <span className="text-gray-300 select-none w-12 text-right pr-6 flex-shrink-0">
                  {idx + 1}
                </span>
                <span className="text-gray-800 whitespace-pre">{line || ' '}</span>
              </div>
            );
          })}
        </div>
      );
    }

    if (fileType === 'excel') {
      if (excelData.length === 0) {
        return (
          <div className="p-12 text-center text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-lg">No data found in Excel file</p>
          </div>
        );
      }

      const currentSheet = excelData[activeSheet];

      return (
        <div className="flex flex-col h-full bg-white">
          {/* Sheet Tabs */}
          <div className="flex overflow-x-auto border-b border-gray-100 px-4 bg-white">
            {excelData.map((sheet, idx) => (
              <button
                key={idx}
                onClick={() => setActiveSheet(idx)}
                className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${activeSheet === idx
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
              >
                {sheet.sheetName}
              </button>
            ))}
          </div>

          {/* Table Data */}
          <div className="flex-1 overflow-auto p-8">
            <table className="min-w-full border-collapse text-sm">
              <tbody>
                {currentSheet.data.map((row, rowIdx) => (
                  <tr key={rowIdx} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                    {row.map((cell: any, cellIdx: number) => {
                      const cellStr = String(cell);
                      const isHighlighted = citation.text_snippet && cellStr.includes(citation.text_snippet);

                      return (
                        <td
                          key={cellIdx}
                          ref={isHighlighted ? (highlightRef as any) : null}
                          className={`px-4 py-3 border-r border-gray-50 last:border-r-0 ${isHighlighted ? 'bg-blue-50 font-medium text-blue-900' : 'text-gray-600'
                            }`}
                        >
                          {cell}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    // Default text view
    return (
      <div className="p-12 font-mono text-sm whitespace-pre-wrap text-gray-800 bg-white leading-relaxed">
        {fileContent}
      </div>
    );
  };

  if (fileType === 'pdf') {
    return (
      <PDFHighlighterViewer
        sessionId={sessionId}
        fileName={normalizedFileName}
        citation={citation}
        onClose={onClose}
      />
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header - Minimalist */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white z-10">
        <div className="flex items-center gap-4 flex-1 min-w-0">
          <div className="p-2 bg-blue-50 rounded-xl">
            {getFileIcon()}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-medium text-gray-900 truncate tracking-tight">{fileName}</h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-600"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Content - Spacious and Clean */}
      <div className="flex-1 overflow-y-auto bg-white scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
        {renderContent()}
      </div>

      {/* Footer - Subtle Citation with dismiss option */}
      {citation.text_snippet && showReferencedContent && (
        <div className="px-8 py-4 border-t border-gray-100 bg-gray-50/50">
          <div className="flex gap-4 items-start max-w-4xl mx-auto">
            <div className="mt-1.5 min-w-[3px] h-10 bg-blue-400 rounded-full opacity-40" />
            <div className="flex-1 min-w-0">
              <span className="font-medium text-gray-500 block mb-1 text-xs uppercase tracking-wider">Citation Source</span>
              <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">
                "{citation.text_snippet.slice(0, 200)}{citation.text_snippet.length > 200 ? '...' : ''}"
              </p>
            </div>
            <button
              onClick={() => setShowReferencedContent(false)}
              className="p-1.5 hover:bg-gray-200 rounded-full transition-colors text-gray-400 hover:text-gray-600 flex-shrink-0"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
