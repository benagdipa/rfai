import React, { useState, useEffect, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import {
  Box,
  CircularProgress,
  Alert,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';

const MapWrapper = styled(Box)(({ theme }) => ({
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

// Custom Leaflet icon for markers (fix default icon issue)
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Dynamic centering component
function MapCenter({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions && positions.length) {
      const bounds = L.latLngBounds(positions);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [map, positions]);
  return null;
}

const NetworkMap = ({
  cells: initialCells = [],
  wsUrl = 'ws://localhost:8000/ws',
  identifier = 'CELL001',
}) => {
  const [cells, setCells] = useState(initialCells);
  const [loading, setLoading] = useState(!initialCells.length);
  const [error, setError] = useState('');

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected for network map updates');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (
        (message.event_type === 'kpis_monitored' || message.event_type === 'issues_detected') &&
        message.data.identifier === identifier
      ) {
        const cellData = {
          identifier: message.data.identifier,
          lat: message.data.lat || 51.505, // Default coordinates if not provided
          lon: message.data.lon || -0.09,
          anomalies_detected: message.data.anomalies_detected || message.data.issues?.length > 0,
        };
        setCells((prev) => {
          const updated = prev.filter((c) => c.identifier !== cellData.identifier);
          return [...updated, cellData];
        });
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
    if (!initialCells.length && !wsUrl) {
      const fetchData = async () => {
        setLoading(true);
        try {
          const response = await fetch(`/api/status/${identifier}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          });
          if (!response.ok) throw new Error('Failed to fetch network data');
          const result = await response.json();
          const cellData = {
            identifier: result.identifier,
            lat: result.lat || 51.505,
            lon: result.lon || -0.09,
            anomalies_detected: result.monitoring?.anomalies_detected || result.issues?.length > 0,
          };
          setCells([cellData]);
          setError('');
        } catch (err) {
          setError(err.message || 'Failed to load network map data');
        } finally {
          setLoading(false);
        }
      };
      fetchData();
    }
  }, [initialCells, identifier]);

  // Memoized positions for centering
  const positions = useMemo(
    () => cells.map((cell) => [cell.lat || 51.505, cell.lon || -0.09]),
    [cells]
  );

  // Custom marker icon based on anomaly status
  const getMarkerIcon = (anomalies_detected) =>
    L.divIcon({
      className: 'custom-marker',
      html: `<div style="background-color: ${anomalies_detected ? 'red' : 'green'}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white;"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
      popupAnchor: [0, -10],
    });

  // Render logic
  if (loading) {
    return (
      <MapWrapper>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          Loading network map...
        </Typography>
      </MapWrapper>
    );
  }

  if (error) {
    return (
      <MapWrapper>
        <Alert severity="error">{error}</Alert>
      </MapWrapper>
    );
  }

  if (!cells.length) {
    return (
      <MapWrapper>
        <Typography>No network map data available</Typography>
      </MapWrapper>
    );
  }

  return (
    <MapWrapper>
      <MapContainer
        center={positions[0] || [51.505, -0.09]}
        zoom={13}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        <MapCenter positions={positions} />
        {cells.map((cell) => (
          <Marker
            key={cell.identifier}
            position={[cell.lat || 51.505, cell.lon || -0.09]}
            icon={getMarkerIcon(cell.anomalies_detected)}
          >
            <Popup>
              <Typography variant="body2">
                <strong>{cell.identifier}</strong>
                <br />
                Anomalies: {cell.anomalies_detected ? 'Yes' : 'No'}
                <br />
                Lat: {cell.lat || 'N/A'}, Lon: {cell.lon || 'N/A'}
              </Typography>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </MapWrapper>
  );
};

export default NetworkMap;