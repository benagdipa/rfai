import React, { useState, useEffect, useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Title,
} from 'chart.js';
import { Box, CircularProgress, Alert, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Title);

const ChartContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[1],
  height: '400px',
  width: '100%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
}));

const PredictionChart = ({
  predictions: initialPredictions = {},
  identifier = 'CELL001',
  wsUrl = 'ws://localhost:8000/ws',
}) => {
  const [predictions, setPredictions] = useState(initialPredictions);
  const [loading, setLoading] = useState(!Object.keys(initialPredictions).length);
  const [error, setError] = useState('');

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected for prediction updates');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.event_type === 'predictions_generated' && message.data.identifier === identifier) {
        setPredictions(message.data.predictions);
        setLoading(false);
        setError('');
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('Failed to connect to real-time prediction updates');
      setLoading(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => ws.close();
  }, [wsUrl, identifier]);

  // Fetch initial predictions if not provided
  useEffect(() => {
    if (!Object.keys(initialPredictions).length && !wsUrl) {
      const fetchPredictions = async () => {
        setLoading(true);
        try {
          const response = await fetch(`/api/predict/${identifier}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          });
          if (!response.ok) throw new Error('Failed to fetch predictions');
          const result = await response.json();
          setPredictions(result.predictions);
          setError('');
        } catch (err) {
          setError(err.message || 'Failed to load prediction data');
        } finally {
          setLoading(false);
        }
      };
      fetchPredictions();
    }
  }, [initialPredictions, identifier]);

  // Memoized chart data for performance
  const chartData = useMemo(() => {
    if (!predictions || !Object.keys(predictions).length) return null;

    const datasets = Object.entries(predictions).map(([key, values]) => ({
      label: `${key} (Predicted)`,
      data: values,
      borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
      backgroundColor: 'transparent',
      borderDash: [5, 5], // Dashed line for predictions
      tension: 0.4, // Smooth lines
      pointRadius: 3,
      fill: false,
    }));

    // Generate future time steps as labels
    const maxLength = Math.max(...datasets.map((ds) => ds.data.length));
    const labels = Array(maxLength)
      .fill('')
      .map((_, i) => `T+${i + 1}`);

    return { labels, datasets };
  }, [predictions]);

  // Chart options
  const options = {
    maintainAspectRatio: false,
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: `Predicted KPIs for ${identifier}`,
        font: { size: 16 },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(2)}`,
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Future Time Steps' },
      },
      y: {
        title: { display: true, text: 'Predicted Value' },
        beginAtZero: false,
      },
    },
  };

  // Render logic
  if (loading) {
    return (
      <ChartContainer>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          Loading predictions...
        </Typography>
      </ChartContainer>
    );
  }

  if (error) {
    return (
      <ChartContainer>
        <Alert severity="error">{error}</Alert>
      </ChartContainer>
    );
  }

  if (!chartData) {
    return (
      <ChartContainer>
        <Typography>No predictions available</Typography>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer>
      <Line data={chartData} options={options} />
    </ChartContainer>
  );
};

export default PredictionChart;