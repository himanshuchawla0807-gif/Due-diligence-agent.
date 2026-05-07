import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText } from 'lucide-react';
import type { Citation } from '../../types';

interface CitationTooltipProps {
    citation: Citation | null;
    isVisible: boolean;
    position: { x: number; y: number };
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;
    onClose?: () => void;
}

export function CitationTooltip({ citation, isVisible, position, onMouseEnter, onMouseLeave, onClose, onOpenDocument }: CitationTooltipProps & { onOpenDocument?: (citation: Citation) => void }) {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (isVisible && e.key === 'Escape' && onClose) {
                onClose();
            }
        };

        if (isVisible) {
            window.addEventListener('keydown', handleEscape);
        }

        return () => {
            window.removeEventListener('keydown', handleEscape);
        };
    }, [isVisible, onClose]);

    if (!mounted || typeof document === 'undefined') return null;
    if (!citation) return null;

    const TOOLTIP_WIDTH = 320;
    const SCREEN_PADDING = 16;
    const BADGE_HEIGHT = 20; // Approximate height of the citation badge
    const GAP = 20; // Gap between badge and tooltip

    // Calculate position adjustments
    let left = position.x - (TOOLTIP_WIDTH / 2);
    // Initial target: Position ABOVE the badge
    // position.y is the top of the badge.
    // We want the bottom of the tooltip to be at (position.y - GAP).
    // CSS transform -100% handles the height.
    let top = position.y - GAP;
    let isFlipped = false;

    // Boundary checks
    if (typeof window !== 'undefined') {
        // Prevent overflow left
        if (left < SCREEN_PADDING) {
            left = SCREEN_PADDING;
        }
        // Prevent overflow right
        if (left + TOOLTIP_WIDTH > window.innerWidth - SCREEN_PADDING) {
            left = window.innerWidth - TOOLTIP_WIDTH - SCREEN_PADDING;
        }

        // Check top overflow
        // If top of tooltip (top - height) would be offscreen, flip to bottom
        // We estimate height or just check if 'top' is too close to 0.
        // Since we use transform -100%, 'top' is the bottom anchor of the tooltip.
        // If 'top' is < 200 (approx tooltip height), we might clip.
        if (top < 200) {
            // Flip to BELOW
            // position.y is top of badge.
            // We want top of tooltip to be at (position.y + BADGE_HEIGHT + GAP)
            top = position.y + BADGE_HEIGHT + GAP;
            isFlipped = true;
        }
    }

    const truncateSnippet = (text: string | undefined, maxLength: number): string => {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength).trim() + '...';
    };

    return createPortal(
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: isFlipped ? -4 : 4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: isFlipped ? -4 : 4 }}
                    transition={{ duration: 0.15, ease: "easeOut" }}
                    className="fixed z-[9997] pointer-events-none"
                    style={{
                        left,
                        top,
                        transform: isFlipped ? 'translateY(0)' : 'translateY(-100%)',
                    }}
                    onMouseEnter={onMouseEnter}
                    onMouseLeave={onMouseLeave}
                >
                    <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-xl border border-gray-200/80 p-0 max-w-sm w-[320px] pointer-events-auto overflow-hidden flex flex-col">
                        {/* Header */}
                        <div className="flex items-center gap-2 p-3 border-b border-gray-100 bg-gray-50/50">
                            <FileText className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
                            <span className="text-xs font-semibold text-gray-700 truncate flex-1">
                                {citation.file_name || 'Unknown Source'}
                            </span>
                            <span className="text-[10px] font-medium bg-white border border-gray-200 text-gray-500 px-1.5 py-0.5 rounded shadow-sm">
                                Page {citation.page}
                            </span>
                        </div>

                        {/* Content */}
                        <div className="p-3 text-sm leading-relaxed text-gray-600 font-medium bg-white">
                            {citation.text_snippet ? (
                                <span className="line-clamp-4">
                                    "{truncateSnippet(citation.text_snippet, 300)}"
                                </span>
                            ) : (
                                <span className="text-gray-400 italic text-xs">
                                    No preview text available
                                </span>
                            )}
                        </div>

                        {/* Footer / Action */}
                        <div className="p-2 bg-gray-50 border-t border-gray-100 flex justify-end">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (onOpenDocument) onOpenDocument(citation);
                                }}
                                className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
                            >
                                View Document
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body
    );
}
