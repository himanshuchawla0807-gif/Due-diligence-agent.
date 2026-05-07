// @ts-nocheck
import React, { useState, useEffect, useRef, Component, ErrorInfo } from 'react';
import { API_BASE_URL } from '@/config';
import 'react-pdf-highlighter-extended/dist/esm/style/PdfHighlighter.css';
import 'react-pdf-highlighter-extended/dist/esm/style/AreaHighlight.css';
import 'react-pdf-highlighter-extended/dist/esm/style/MouseSelection.css';
import 'react-pdf-highlighter-extended/dist/esm/style/TextHighlight.css';
import 'react-pdf-highlighter-extended/dist/esm/style/pdf_viewer.css';
import {
    PdfLoader,
    PdfHighlighter,
    Highlight,
    AreaHighlight,
    useHighlightContainerContext,
} from 'react-pdf-highlighter-extended';
import * as pdfjs from 'pdfjs-dist';
import type { Citation } from '../../types';
import { X, AlertTriangle, Loader2 } from 'lucide-react';

// Configure worker with explicit version to match package.json (4.4.168)
// Using local file to ensure reliability and matching version
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

interface PDFHighlighterViewerProps {
    sessionId: string;
    fileName: string;
    citation: Citation;
    onClose: () => void;
}

// Simple Error Boundary to catch render errors in the PDF viewer
class ViewerErrorBoundary extends Component<{ children: React.ReactNode }, { hasError: boolean, error: Error | null }> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error) {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("PDF Viewer crashed:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="h-full flex flex-col items-center justify-center bg-gray-50 p-8 text-center">
                    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 max-w-md">
                        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">PDF Viewer Error</h3>
                        <p className="text-gray-500 mb-4">Something went wrong while displaying this document.</p>
                        <div className="bg-gray-100 p-3 rounded text-xs font-mono text-left overflow-auto max-h-32 mb-4">
                            {this.state.error?.message || "Unknown error"}
                        </div>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}

const HighlightContainer = () => {
    const { highlight, isScrolledTo } = useHighlightContainerContext();

    return (
        <AreaHighlight
            isScrolledTo={isScrolledTo}
            highlight={highlight}
            onChange={(boundingRect) => {
                console.log('Highlight changed', boundingRect);
            }}
        />
    );
};

export function PDFHighlighterViewer({ sessionId, fileName, citation, onClose }: PDFHighlighterViewerProps) {
    const [highlights, setHighlights] = useState<Array<Highlight>>([]);
    const highlighterUtilsRef = useRef<PdfHighlighterUtils>();

    // ✅ AUTH: Get user_id from URL to authorize document fetch
    // This is passed from parent usually, but we can also grab from URL as fallback
    let userId = new URLSearchParams(window.location.search).get('user');
    const documentUrl = userId
        ? `${API_BASE_URL}/api/document/${sessionId}/${fileName}?user_id=${userId}`
        : `${API_BASE_URL}/api/document/${sessionId}/${fileName}`;

    // Handle missing or unresolved documents
    if (fileName === 'Source Document' || fileName === 'Unknown Document') {
        return (
            <div className="h-full flex flex-col bg-gray-50 relative">
                <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white shadow-sm z-10">
                    <h3 className="text-sm font-medium text-gray-700 truncate max-w-md">Document Not Available</h3>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-100 rounded-full text-gray-500"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>
                <div className="flex-1 flex items-center justify-center p-8 text-center">
                    <div className="max-w-md">
                        <div className="mx-auto w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
                            <span className="text-2xl">⚠️</span>
                        </div>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Source Document Not Found</h3>
                        <p className="text-gray-500 mb-4">
                            The system could not resolve the specific source document for this citation.
                            This usually happens when the citation metadata is incomplete.
                        </p>
                        <div className="bg-white p-4 rounded border border-gray-200 text-left">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Cited Text</p>
                            <p className="text-sm text-gray-700 italic">"{citation.text_snippet}"</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Convert citation to highlight format
    useEffect(() => {
        if (citation.bbox && citation.page) {
            const newHighlight: Highlight = {
                id: citation.id || 'temp-highlight',
                content: { text: citation.text_snippet },
                position: {
                    boundingRect: {
                        x1: citation.bbox.x1 * 100,
                        y1: citation.bbox.y1 * 100,
                        x2: citation.bbox.x2 * 100,
                        y2: citation.bbox.y2 * 100,
                        width: (citation.bbox.x2 - citation.bbox.x1) * 100,
                        height: (citation.bbox.y2 - citation.bbox.y1) * 100,
                    },
                    rects: [
                        {
                            x1: citation.bbox.x1 * 100,
                            y1: citation.bbox.y1 * 100,
                            x2: citation.bbox.x2 * 100,
                            y2: citation.bbox.y2 * 100,
                            width: (citation.bbox.x2 - citation.bbox.x1) * 100,
                            height: (citation.bbox.y2 - citation.bbox.y1) * 100,
                        }
                    ],
                    pageNumber: citation.page,
                },
                comment: { text: 'Citation Source', emoji: '📌' },
            };
            setHighlights([newHighlight]);
        } else {
            setHighlights([]);
        }
    }, [citation]);

    // Scroll to highlight when it changes
    useEffect(() => {
        if (highlights.length > 0 && highlighterUtilsRef.current) {
            const highlight = highlights[0];
            // Small timeout to ensure PDF is loaded and rendered
            setTimeout(() => {
                highlighterUtilsRef.current?.scrollToHighlight(highlight);
            }, 500);
        }
    }, [highlights]);

    return (
        <ViewerErrorBoundary>
            <div className="h-full flex flex-col bg-gray-50 relative">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white shadow-sm z-10">
                    <h3 className="text-sm font-medium text-gray-700 truncate max-w-md">{fileName}</h3>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-gray-100 rounded-full text-gray-500"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex-1 relative overflow-hidden">
                    <PdfLoader
                        document={documentUrl}
                        beforeLoad={(pdfDocument) => (
                            <div className="flex items-center justify-center h-full text-gray-500">
                                <Loader2 className="w-8 h-8 animate-spin mr-2 text-blue-500" />
                                <span>Loading PDF...</span>
                            </div>
                        )}
                        errorMessage={(error) => (
                            <div className="flex items-center justify-center h-full text-red-500 p-8 text-center">
                                <div>
                                    <AlertTriangle className="w-10 h-10 mx-auto mb-2" />
                                    <p className="font-medium">Failed to load PDF</p>
                                    <p className="text-sm mt-1 text-gray-400">Please check if the file exists and is accessible.</p>
                                    <p className="text-xs mt-2 text-gray-300">{error.message}</p>
                                </div>
                            </div>
                        )}
                        onError={(e) => console.error("PDF Load Error:", e)}
                    >
                        {(pdfDocument) => (
                            <PdfHighlighter
                                pdfDocument={pdfDocument}
                                enableAreaSelection={(event) => event.altKey}
                                highlights={highlights}
                                utilsRef={(utils) => {
                                    highlighterUtilsRef.current = utils;
                                }}
                            >
                                <HighlightContainer />
                            </PdfHighlighter>
                        )}
                    </PdfLoader>
                </div>
            </div>
        </ViewerErrorBoundary>
    );
}
