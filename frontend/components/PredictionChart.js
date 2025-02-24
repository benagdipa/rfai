import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Tooltip } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

const PredictionChart = ({ predictions }) => {
  if (!predictions || Object.keys(predictions).length === 0) return <div>No predictions available</div>;

  const datasets = Object.entries(predictions).map(([key, values]) => ({
    label: `${key} (Predicted)`,
    data: values,
    borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
    borderDash: [5, 5],
  }));

  const chartData = {
    labels: Array(datasets[0].data.length).fill('').map((_, i) => `T+${i+1}`),
    datasets,
  };

  return (
    <div style={{ height: '400px', width: '100%' }}>
      <Line data={chartData} options={{ maintainAspectRatio: false }} />
    </div>
  );
};

export default PredictionChart;
