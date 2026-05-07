import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ExternalLink, X, Copy, Check, AlertCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Citation } from '../../types';

interface CitationPopoverProps {
    citation: Citation | null;
    onClose: () => void;
    onOpenDocument: (citation: Citation) => void;
    onDocumentSelect?: (documentPath: string) => void;
}

export function CitationPopover({ citation, onClose, onOpenDocument, onDocumentSelect }: CitationPopoverProps) {
    const [mounted, setMounted] = useState(false);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        setMounted(true);
        return () => setMounted(false);
    }, []);

    if (!mounted || !citation) return null;

    const hasFileName = !!citation.file_name;
    const hasSnippet = !!citation.text_snippet && citation.text_snippet.trim().length > 0;

    const handleCopy = () => {
        if (citation.text_snippet) {
            navigator.clipboard.writeText(citation.text_snippet);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    // Helper to parse and render structured data
    const renderStructuredContent = (text: string) => {
        if (!text) return null;

        // Check if we can highlight the snippet within the full text
        const snippet = citation.text_snippet || "";
        // Simple normalization for matching
        const normalize = (s: string) => s.replace(/\s+/g, ' ').trim();

        if (snippet && text.length > snippet.length) {
            const normalizedText = normalize(text);
            const normalizedSnippet = normalize(snippet);

            if (normalizedText.includes(normalizedSnippet)) {
                // Find the snippet in the original text (best effort)
                // This is tricky because normalization loses exact indices.
                // We'll try a simple split first.
                const parts = text.split(snippet);
                if (parts.length > 1) {
                    return (
                        <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap font-mono">
                            {parts.map((part, i) => (
                                <React.Fragment key={i}>
                                    {part}
                                    {i < parts.length - 1 && (
                                        <span className="bg-yellow-100 text-gray-900 font-semibold px-1 rounded">
                                            {snippet}
                                        </span>
                                    )}
                                </React.Fragment>
                            ))}
                        </div>
                    );
                }
            }
        }

        // Fallback to existing rendering logic if no highlight match
        const lines = text.split('\n').map(l => l.trim()).filter(l => l);
        const hasStructure = lines.some(l => l.includes(':') || /\s{2,}/.test(l));

        if (!hasStructure) {
            // Fallback to Markdown for regular text
            const cleanSnippet = text
                .replace(/(\n\s*[-*]|\n\s*\d+\.)/g, '§§LIST_ITEM§§$1')
                .replace(/([^\n])\n([^\n])/g, '$1 $2')
                .replace(/§§LIST_ITEM§§/g, '')
                .replace(/\n{3,}/g, '\n\n');

            return (
                <div className="prose prose-base max-w-none text-gray-800 leading-relaxed">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            p: ({ children }) => <p className="mb-4 last:mb-0 text-base leading-7 text-gray-800">{children}</p>,
                            h1: ({ children }) => <h1 className="text-xl font-bold mt-6 mb-3 text-gray-900">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-lg font-bold mt-5 mb-2 text-gray-900">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-base font-bold mt-4 mb-2 text-gray-900 uppercase tracking-wide">{children}</h3>,
                            ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-2 text-base">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-2 text-base">{children}</ol>,
                            li: ({ children }) => <li className="pl-1">{children}</li>,
                            strong: ({ children }) => <span className="bg-yellow-100 text-gray-900 font-bold px-1 rounded box-decoration-clone">{children}</span>,
                            blockquote: ({ children }) => <blockquote className="border-l-4 border-blue-200 pl-4 italic my-4 text-gray-600 bg-blue-50/30 py-3 pr-3 rounded-r">{children}</blockquote>,
                            code: ({ children }) => <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800 border border-gray-200">{children}</code>,
                        }}
                    >
                        {cleanSnippet}
                    </ReactMarkdown>
                </div>
            );
        }

        // Parse structured data into rows
        const rows: React.ReactNode[] = [];
        let i = 0;

        while (i < lines.length) {
            const line = lines[i];

            // Case 1: Section Header
            if (line.match(/^\d+\./) || (line === line.toUpperCase() && line.length > 5 && !line.includes(':'))) {
                rows.push(
                    <tr key={`header-${i}`} className="bg-gray-50">
                        <td colSpan={2} className="py-4 px-4 border-b border-gray-200">
                            <h3 className="text-lg font-bold text-blue-800 uppercase tracking-wide m-0">
                                {line}
                            </h3>
                        </td>
                    </tr>
                );
                i++;
                continue;
            }

            // Case 2: Key-Value Pair
            let key = '';
            let value = '';
            let match = false;

            const colonIndex = line.indexOf(':');
            const spaceMatch = line.match(/\s{2,}/);
            const spaceIndex = (spaceMatch && typeof spaceMatch.index === 'number') ? spaceMatch.index : -1;

            if (colonIndex !== -1) {
                key = line.substring(0, colonIndex).trim();
                value = line.substring(colonIndex + 1).trim();
                match = true;

                if (!value && i + 1 < lines.length) {
                    const nextLine = lines[i + 1];
                    if (!nextLine.includes(':') && !nextLine.match(/^\d+\./)) {
                        value = nextLine.trim();
                        i++;
                    }
                }
            } else if (spaceIndex !== -1) {
                key = line.substring(0, spaceIndex).trim();
                value = line.substring(spaceIndex).trim();
                match = true;
            }

            if (match) {
                const isNA = !value || value.toLowerCase() === 'n/a' || value.toLowerCase() === 'none';

                rows.push(
                    <tr key={`kv-${i}`} className="hover:bg-gray-50/50 transition-colors">
                        <td className="py-3 px-4 border-b border-gray-100 w-1/3 align-top">
                            <span className="font-bold text-gray-700 text-sm uppercase tracking-wide block">
                                {key}
                            </span>
                        </td>
                        <td className="py-3 px-4 border-b border-gray-100 align-top">
                            {isNA ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-100">
                                    <AlertCircle className="w-3 h-3 mr-1" />
                                    Missing / N/A
                                </span>
                            ) : (
                                <span className="text-gray-900 font-medium text-base leading-relaxed block">
                                    {value}
                                </span>
                            )}
                        </td>
                    </tr>
                );
            } else {
                rows.push(
                    <tr key={`p-${i}`}>
                        <td colSpan={2} className="py-2 px-4 border-b border-gray-100">
                            <p className="text-gray-600 leading-relaxed">{line}</p>
                        </td>
                    </tr>
                );
            }
            i++;
        }

        return (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <tbody>{rows}</tbody>
                </table>
            </div>
        );
    };

    const content = (
        <AnimatePresence>
            {citation && (
                <>
                    {/* Z-index hierarchy: Tooltip (9997) < Backdrop (9998) < Popover (9999) */}
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[9998]"
                    />

                    {/* Popover Card - Centered */}
                    <div className="fixed inset-0 flex items-center justify-center z-[9999] pointer-events-none p-4">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            transition={{ type: "spring", duration: 0.4, bounce: 0.3 }}
                            className="bg-white shadow-2xl rounded-xl w-full max-w-4xl overflow-hidden pointer-events-auto ring-1 ring-black/10 flex flex-col max-h-[85vh]"
                        >
                            {/* Header Section */}
                            <div className="px-8 py-6 bg-white">
                                <div className="flex justify-between items-start">
                                    <div className="flex-1 min-w-0 mr-4">
                                        {/* Title */}
                                        <h2 className="text-2xl font-bold text-blue-700 leading-tight mb-2 truncate">
                                            {citation.file_name || 'Source Document'}
                                        </h2>

                                        {/* Subtitle */}
                                        <div className="flex items-center flex-wrap gap-2 text-base font-medium text-gray-500">
                                            <span className="flex items-center gap-1.5">
                                                <FileText className="w-4 h-4" />
                                                {citation.file_name ? 'Document' : 'Unknown Source'}
                                            </span>
                                            {citation.page > 0 && (
                                                <>
                                                    <span className="text-gray-300">•</span>
                                                    <span>Page {citation.page}</span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                    <button
                                        onClick={onClose}
                                        className="p-2 -mr-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-600 flex-shrink-0"
                                    >
                                        <X className="w-6 h-6" />
                                    </button>
                                </div>
                            </div>

                            {/* Divider */}
                            <div className="h-px bg-gray-100 mx-8" />

                            {/* Content Section */}
                            <div className="flex-1 overflow-y-auto px-8 py-6 bg-white">
                                {/* Context Banner Removed per user request */}

                                {hasSnippet ? (
                                    renderStructuredContent(citation.full_context || citation.text_snippet || '')
                                ) : (
                                    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                                        <FileText className="w-16 h-16 mb-4 opacity-20" />
                                        <p className="text-base italic">No text preview available for this citation.</p>
                                    </div>
                                )}
                            </div>

                            {/* Footer Section - Actions */}
                            <div className="px-8 py-5 bg-gray-50 border-t border-gray-100 flex justify-end items-center gap-3">
                                <button
                                    onClick={handleCopy}
                                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors shadow-sm"
                                >
                                    {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                                    <span>{copied ? 'Copied' : 'Copy Text'}</span>
                                </button>

                                <button
                                    onClick={() => {
                                        if (hasFileName) {
                                            if (onDocumentSelect && citation.relative_path) {
                                                onDocumentSelect(citation.relative_path);
                                            } else {
                                                onOpenDocument(citation);
                                            }
                                            onClose();
                                        }
                                    }}
                                    disabled={!hasFileName}
                                    className={`flex items-center gap-2 px-6 py-2.5 text-sm font-bold rounded-lg shadow-sm transition-all ${hasFileName
                                        ? 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-md active:scale-[0.98]'
                                        : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                        }`}
                                >
                                    <span>Open Full Document</span>
                                    <ExternalLink className="w-4 h-4" />
                                </button>
                            </div>
                        </motion.div>
                    </div>
                </>
            )}
        </AnimatePresence>
    );

    return createPortal(content, document.body);
}
