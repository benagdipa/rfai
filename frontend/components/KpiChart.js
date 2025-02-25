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
import { Box, Typography, CircularProgress, Alert } from '@mui/material';
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

const KpiChart = ({ data: initialData, identifier = 'CELL001', wsUrl = 'ws://localhost:8000/ws' }) => {
  const [data, setData] = useState(initialData || {});
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState('');

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected for KPI updates');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.event_type === 'kpis_monitored' && message.data.identifier === identifier) {
        setData(message.data);
        setLoading(false);
        setError('');
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('Failed to connect to real-time updates');
      setLoading(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => ws.close();
  }, [wsUrl, identifier]);

  // Fetch initial data if not provided
  useEffect(() => {
    if (!initialData && !wsUrl) {
      const fetchData = async () => {
        setLoading(true);
        try {
          const response = await fetch(`/api/monitor/${identifier}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          });
          if (!response.ok) throw new Error('Failed to fetch KPI data');
          const result = await response.json();
          setData(result);
          setError('');
        } catch (err) {
          setError(err.message || 'Failed to load KPI data');
        } finally {
          setLoading(false);
        }
      };
      fetchData();
    }
  }, [initialData, identifier]);

  // Prepare chart data memoized for performance
  const chartData = useMemo(() => {
    if (!data || !data.summary) return null;

    const numericCols = Object.keys(data.summary).filter(
      (key) => typeof data.summary[key].mean === 'number'
    );
    if (!numericCols.length) return null;

    // Use timestamp or index as labels if available
    const labels = data.timestamps
      ? data.timestamps.map((ts) => new Date(ts).toLocaleTimeString())
      : Array(Math.max(...numericCols.map((col) => data.summary[col].count))).fill('').map((_, i) => i);

    return {
      labels,
      datasets: numericCols.map((col) => ({
        label: col,
        data: Object.values(data.summary[col]), // Assumes summary has values like mean, min, max, etc.
        borderColor: `hsl(${Math.random() * 360}, 70%, 50%)`,
        backgroundColor: 'transparent',
        tension: 0.4, // Smooth lines
        pointRadius: 3,
        fill: false,
      })),
    };
  }, [data]);

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
        text: `KPI Trends for ${identifier}`,
        font: { size: 16 },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Time/Index' },
      },
      y: {
        title: { display: true, text: 'Value' },
        beginAtZero: true,
      },
    },
  };

  // Render logic
  if (loading) {
    return (
      <ChartContainer>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          Loading KPI data...
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
        <Typography>No numeric KPI data available</Typography>
      </ChartContainer>
    );
  }

  return (
    <ChartContainer>
      <Line data={chartData} options={options} />
    </ChartContainer>
  );
};

export default KpiChart;