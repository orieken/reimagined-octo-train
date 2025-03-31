// src/components/charts/PassRateChart.jsx
import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LabelList
} from 'recharts';

const PassRateChart = ({ features }) => {
  if (!features || features.length === 0) {
    return <div className="text-center py-8 text-secondary">No data available</div>;
  }

  // Process the data to calculate pass rates
  const data = features.map(feature => {
    const totalTests = feature.passed + feature.failed + feature.skipped;
    const passRate = (feature.passed / totalTests) * 100;

    return {
      name: feature.name,
      passRate: Math.round(passRate * 10) / 10, // Round to 1 decimal place
      totalTests
    };
  });

  // Sort by pass rate descending
  data.sort((a, b) => b.passRate - a.passRate);

  // Generate color based on pass rate value
  const getBarColor = (value) => {
    if (value >= 90) return '#48BB78'; // success
    if (value >= 75) return '#38B2AC'; // success-lighter
    if (value >= 60) return '#ECC94B'; // warning
    return '#F56565'; // danger
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        layout="vertical"
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
        <XAxis type="number" domain={[0, 100]} />
        <YAxis
          dataKey="name"
          type="category"
          width={100}
          tick={{ fontSize: 12 }}
        />
        <Tooltip
          formatter={(value) => [`${value}%`, 'Pass Rate']}
          labelFormatter={(value) => `Feature: ${value}`}
          cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
        />
        <Bar dataKey="passRate" name="Pass Rate">
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getBarColor(entry.passRate)} />
          ))}
          <LabelList dataKey="passRate" position="right" formatter={(value) => `${value}%`} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default PassRateChart;