// src/components/charts/TestResultsPieChart.jsx
import React from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer,
  Tooltip, Legend
} from 'recharts';

const TestResultsPieChart = ({ passed, failed, skipped }) => {
  if (!passed && !failed && !skipped) {
    return <div className="text-center py-8 text-secondary">No data available</div>;
  }

  const data = [
    { name: 'Passed', value: passed, color: '#48BB78' }, // success
    { name: 'Failed', value: failed, color: '#F56565' }, // danger
    { name: 'Skipped', value: skipped, color: '#ECC94B' } // warning
  ].filter(item => item.value > 0); // Filter out zero values

  const total = passed + failed + skipped;

  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomizedLabel}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [`${value} tests (${(value/total*100).toFixed(1)}%)`, '']}
          />
          <Legend
            layout="horizontal"
            verticalAlign="bottom"
            align="center"
            formatter={(value, entry, index) => {
              const item = data[index];
              return <span style={{ color: entry.color }}>{`${value}: ${item.value} tests`}</span>;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TestResultsPieChart;