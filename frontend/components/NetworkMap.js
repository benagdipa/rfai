import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const NetworkMap = ({ cells }) => {
  if (!cells || !cells.length) return <div>No map data</div>;

  return (
    <MapContainer center={[51.505, -0.09]} zoom={13} style={{ height: '400px', width: '100%' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {cells.map(cell => (
        <Marker key={cell.identifier} position={[cell.lat || 51.505, cell.lon || -0.09]}>
          <Popup>{cell.identifier} - Anomalies: {cell.anomalies_detected ? 'Yes' : 'No'}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};

export default NetworkMap;
