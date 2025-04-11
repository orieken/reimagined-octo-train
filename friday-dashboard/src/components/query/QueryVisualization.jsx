// src/components/query/QueryVisualization.jsx
import React from 'react';
import PropTypes from 'prop-types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const QueryVisualization = ({ chartData }) => {
  if (!chartData || !chartData.type || !chartData.data) {
    return null;
  }

  const renderChart = () => {
    switch (chartData.type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={chartData.data}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={chartData.xAxis || 'name'} />
              <YAxis />
              <Tooltip />
              <Legend />
              {chartData.series
                ? chartData.series.map((series, index) => (
                  <Bar
                    key={series.dataKey}
                    dataKey={series.dataKey}
                    fill={series.color || COLORS[index % COLORS.length]}
                    name={series.name || series.dataKey}
                  />
                ))
                : [
                  <Bar
                    key="default"
                    dataKey={chartData.dataKey || 'value'}
                    fill={COLORS[0]}
                    name={chartData.name || 'Value'}
                  />
                ]}
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={chartData.data}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={chartData.xAxis || 'name'} />
              <YAxis />
              <Tooltip />
              <Legend />
              {chartData.series
                ? chartData.series.map((series, index) => (
                  <Line
                    key={series.dataKey}
                    type="monotone"
                    dataKey={series.dataKey}
                    stroke={series.color || COLORS[index % COLORS.length]}
                    name={series.name || series.dataKey}
                    activeDot={{ r: 8 }}
                  />
                ))
                : [
                  <Line
                    key="default"
                    type="monotone"
                    dataKey={chartData.dataKey || 'value'}
                    stroke={COLORS[0]}
                    name={chartData.name || 'Value'}
                    activeDot={{ r: 8 }}
                  />
                ]}
            </LineChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData.data}
                cx="50%"
                cy="50%"
                labelLine={true}
                outerRadius={80}
                fill="#8884d8"
                dataKey={chartData.dataKey || 'value'}
                nameKey={chartData.nameKey || 'name'}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {chartData.data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color || COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      default:
        return (
          <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
            <p className="text-gray-500">Unsupported chart type: {chartData.type}</p>
          </div>
        );
    }
  };

  return (
    <div className="query-visualization">
      <h3 className="text-lg font-semibold mb-3">{chartData.title || 'Visualization'}</h3>
      {renderChart()}
      {chartData.description && (
        <p className="mt-2 text-sm text-gray-600">{chartData.description}</p>
      )}
    </div>
  );
};

QueryVisualization.propTypes = {
  chartData: PropTypes.shape({
    type: PropTypes.oneOf(['bar', 'line', 'pie']).isRequired,
    data: PropTypes.array.isRequired,
    title: PropTypes.string,
    description: PropTypes.string,
    xAxis: PropTypes.string,
    dataKey: PropTypes.string,
    nameKey: PropTypes.string,
    series: PropTypes.arrayOf(
      PropTypes.shape({
        dataKey: PropTypes.string.isRequired,
        name: PropTypes.string,
        color: PropTypes.string
      })
    )
  })
};

export default QueryVisualization;