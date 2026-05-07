import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Briefcase, TrendingUp, Building2, X } from 'lucide-react'

interface IndustrySelectorProps {
    value: "PE" | "VC" | "FO" | null
    onChange: (industry: "PE" | "VC" | "FO" | null) => void
    className?: string
}

export function IndustrySelector({ value, onChange, className }: IndustrySelectorProps) {
    const industries = [
        { id: "PE", label: "Private Equity", icon: Briefcase },
        { id: "VC", label: "Venture Capital", icon: TrendingUp },
        { id: "FO", label: "Family Office", icon: Building2 },
    ] as const

    return (
        <div className={cn("flex flex-wrap gap-2 items-center justify-center p-2 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-200 dark:border-slate-800", className)}>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 mr-2 uppercase tracking-wider">
                Select Agent:
            </span>

            {industries.map((industry) => {
                const isSelected = value === industry.id
                const Icon = industry.icon

                return (
                    <button
                        key={industry.id}
                        onClick={() => onChange(isSelected ? null : industry.id)}
                        className={cn(
                            "relative flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                            isSelected
                                ? "bg-blue-500 text-white shadow-md shadow-blue-500/20"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                        )}
                    >
                        <Icon className="w-3.5 h-3.5" />
                        {industry.label}
                        {isSelected && (
                            <motion.div
                                layoutId="active-indicator"
                                className="absolute inset-0 rounded-full bg-blue-500 -z-10"
                                transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                            />
                        )}
                    </button>
                )
            })}

            {value && (
                <button
                    onClick={() => onChange(null)}
                    className="ml-2 p-1 rounded-full hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 transition-colors"
                    title="Clear selection"
                >
                    <X className="w-3.5 h-3.5" />
                </button>
            )}
        </div>
    )
}
