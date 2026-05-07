import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { GraphStep } from '@/types';

interface ThinkingProcessProps {
    steps: GraphStep[];
}

export function ThinkingProcess({ steps }: ThinkingProcessProps) {
    const [isOpen, setIsOpen] = useState(false);

    if (!steps || steps.length === 0) return null;

    return (
        <div className="mb-4 rounded-lg overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-1 py-1 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
                {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                <span>Thought Process</span>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                    >
                        <div className="pl-2 py-2 space-y-3 border-l-2 border-gray-200 ml-1.5 mt-1">
                            {steps.map((step, index) => (
                                <div key={index} className="relative pl-4">
                                    <div className="absolute -left-[5px] top-1.5 w-2 h-2 rounded-full bg-gray-300 ring-2 ring-white" />

                                    <div className="mb-1 font-medium text-gray-700 text-xs flex items-center gap-1">
                                        <span>{step.action || "Action"}</span>
                                    </div>

                                    <div className="mb-2 font-mono text-[10px] text-gray-500 bg-gray-50 p-1.5 rounded border border-gray-100 overflow-x-auto">
                                        {JSON.stringify(step.tool_input || {}, null, 2)}
                                    </div>

                                    {step.observation && (
                                        <div className="text-gray-600">
                                            <div className="whitespace-pre-wrap font-mono text-[10px] text-gray-500">
                                                {typeof step.observation === 'string'
                                                    ? (step.observation.length > 300 ? step.observation.substring(0, 300) + "..." : step.observation)
                                                    : JSON.stringify(step.observation)}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
