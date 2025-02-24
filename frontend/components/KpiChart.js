import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

const KpiChart = ({ data }) => {
  if (!data || !data.summary) return <div>No data available</div>;

  const numericCols = Object.keys(data.summary).filter(key => typeof data.summary[key].mean === 'number');
  if (!numericCols.length) return <div>No numeric data</div>;

  const chartData = {
    labels: Array(Math.max(...numericCols.map(col => data.summary[col].count))).fill('').map((_, i) => i),
    datasets: numericCols.map(col => ({
      label: col,
      data: Object.values(data.summary[col]),
      borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
    })),
  };

  return (
    <div style={{ height: '400px', width: '100%' }}>
      <Line data={chartData} options={{ maintainAspectRatio: false }} />
    </div>
  );
};

export default KpiChart;
