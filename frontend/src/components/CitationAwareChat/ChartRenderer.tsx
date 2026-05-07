import React from 'react';
import {
    PieChart, Pie, Cell,
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    LineChart, Line,
    ResponsiveContainer,
    LabelList
} from 'recharts';

interface ChartRendererProps {
    chartType: string;
    data: any[];
    title?: string;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export const ChartRenderer: React.FC<ChartRendererProps> = ({ chartType, data, title }) => {
    // Validate data
    if (!data || data.length === 0) {
        console.warn('[ChartRenderer] No data provided');
        return null;
    }

    // Validate data format
    const hasValidData = data.every(item =>
        item &&
        typeof item === 'object' &&
        'name' in item &&
        'value' in item &&
        typeof item.value === 'number' &&
        !isNaN(item.value)
    );

    if (!hasValidData) {
        console.error('[ChartRenderer] Invalid data format:', data);
        return (
            <div className="my-6 p-4 bg-red-50 rounded-lg border border-red-200">
                <p className="text-red-600 text-sm">Invalid chart data format</p>
            </div>
        );
    }

    console.log(`[ChartRenderer] Rendering ${chartType} chart with ${data.length} data points:`, data);

    const cleanLabel = (label: string) => {
        if (typeof label !== 'string') return label;
        return label.replace(/\*\*/g, '').trim();
    };

    const formatValue = (value: number) => {
        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
        if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
        return value.toString();
    };

    const renderChart = () => {
        try {
            switch (chartType.toLowerCase()) {
                case 'pie':
                    return (
                        <ResponsiveContainer width="100%" height={400}>
                            <PieChart>
                                <Pie
                                    data={data}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={false}  // ✅ FIX: Remove inline labels to prevent overlap
                                    outerRadius={130}  // ✅ Larger pie for better visibility
                                    innerRadius={60}   // ✅ Donut style like Research Agent
                                    fill="#8884d8"
                                    dataKey="value"
                                    paddingAngle={2}   // ✅ Slight gap between slices
                                >
                                    {data.map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value: number, name: string) => [formatValue(value), cleanLabel(name)]}
                                    contentStyle={{
                                        backgroundColor: '#ffffff',
                                        border: '1px solid #e5e7eb',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                                        padding: '10px 14px'
                                    }}
                                    labelStyle={{ color: '#1f2937', fontWeight: 600, marginBottom: '4px' }}
                                    itemStyle={{ color: '#374151', fontSize: '13px' }}
                                />
                                <Legend
                                    formatter={cleanLabel}
                                    layout="horizontal"
                                    verticalAlign="bottom"
                                    align="center"
                                    wrapperStyle={{ paddingTop: '20px' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    );
                case 'bar':
                    return (
                        <ResponsiveContainer width="100%" height={400}>
                            <BarChart data={data} margin={{ top: 30, right: 30, left: 20, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                                <XAxis
                                    dataKey="name"
                                    tickFormatter={cleanLabel}
                                    interval={0}
                                    tick={{ fontSize: 12, fill: '#374151', fontWeight: 500 }}
                                    tickLine={{ stroke: '#9CA3AF' }}
                                />
                                <YAxis tickFormatter={formatValue} width={70} tick={{ fill: '#374151', fontWeight: 500 }} />
                                <Tooltip
                                    formatter={(value: number, name: string) => [formatValue(value), cleanLabel(name)]}
                                    labelFormatter={cleanLabel}
                                    cursor={{ fill: 'rgba(99, 102, 241, 0.08)' }}
                                    contentStyle={{
                                        backgroundColor: '#ffffff',
                                        border: '1px solid #e5e7eb',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                                        padding: '10px 14px'
                                    }}
                                    labelStyle={{ color: '#1f2937', fontWeight: 600, marginBottom: '4px' }}
                                    itemStyle={{ color: '#374151', fontSize: '13px' }}
                                />
                                <Bar dataKey="value" name="Value" fill="#6366f1" radius={[4, 4, 0, 0]}>
                                    <LabelList dataKey="value" position="top" formatter={formatValue} style={{ fill: '#9CA3AF', fontSize: 11, fontWeight: 500 }} />
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    );
                case 'line':
                    return (
                        <ResponsiveContainer width="100%" height={450}>
                            <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="name" tickFormatter={cleanLabel} />
                                <YAxis tickFormatter={formatValue} width={80} />
                                <Tooltip formatter={(value: number) => [formatValue(value), 'Value']} labelFormatter={cleanLabel} />
                                <Legend formatter={cleanLabel} />
                                <Line type="monotone" dataKey="value" name="Value" stroke="#6366f1" strokeWidth={3} activeDot={{ r: 8 }}>
                                    <LabelList dataKey="value" position="top" formatter={formatValue} style={{ fill: '#4b5563', fontSize: 12 }} />
                                </Line>
                            </LineChart>
                        </ResponsiveContainer>
                    );
                default:
                    console.error(`[ChartRenderer] Unsupported chart type: ${chartType}`);
                    return <div className="text-amber-600">Unsupported chart type: {chartType}</div>;
            }
        } catch (error) {
            console.error('[ChartRenderer] Error rendering chart:', error);
            return (
                <div className="my-6 p-4 bg-red-50 rounded-lg border border-red-200">
                    <p className="text-red-600 text-sm">Chart rendering error: {String(error)}</p>
                </div>
            );
        }
    };

    return (
        <div className="my-6 p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
            {title && (
                <h4 className="text-lg font-semibold mb-4 text-center">
                    {title}
                    <span className="text-xs text-gray-400 ml-2">({data.length} items)</span>
                </h4>
            )}
            {renderChart()}
        </div>
    );
};
