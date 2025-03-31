// src/components/charts/TagsBarChart.jsx
import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';

const TagsBarChart = ({ tags }) => {
  if (!tags || tags.length === 0) {
    return <div className="text-center py-8 text-secondary">No data available</div>;
  }

  // Sort tags by count in descending order
  const sortedTags = [...tags].sort((a, b) => b.count - a.count);

  // Process the data for the chart
  const data = sortedTags.map(tag => ({
    name: tag.name,
    count: tag.count,
    passRate: tag.passRate
  }));

  // Calculate the average pass rate for the reference line
  const averagePassRate = data.reduce((sum, item) => sum + item.passRate, 0) / data.length;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis yAxisId="left" orientation="left" />
        <YAxis yAxisId="right" orientation="right" domain={[0, 100]} />
        <Tooltip
          formatter={(value, name) => {
            if (name === 'count') return [`${value} tests`, 'Test Count'];
            if (name === 'passRate') return [`${value}%`, 'Pass Rate'];
            return [value, name];
          }}
        />
        <Legend />
        <Bar yAxisId="left" dataKey="count" name="Test Count" fill="#3182CE" barSize={30} />
        <Bar yAxisId="right" dataKey="passRate" name="Pass Rate (%)" fill="#48BB78" barSize={30} />
        <ReferenceLine
          yAxisId="right"
          y={averagePassRate}
          label={{
            position: 'right',
            value: `Avg: ${averagePassRate.toFixed(1)}%`,
            fill: '#4A5568',
            fontSize: 12
          }}
          stroke="#4A5568"
          strokeDasharray="3 3"
        />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default TagsBarChart;