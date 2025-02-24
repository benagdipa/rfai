import { useState } from 'react';
import {
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Input,
  FormHelperText,
} from '@mui/material';
import api from '../lib/api';

export default function DataSourceConfig({ onSubmit }) {
  const [sourceType, setSourceType] = useState('csv');
  const [config, setConfig] = useState({});
  const [fileError, setFileError] = useState('');
  const [file, setFile] = useState(null);

  const handleConfigChange = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
    if (key === 'file_path') setFileError('');
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
        handleConfigChange('file_path', selectedFile.name);
        setFileError('');
      } else {
        setFileError('Please select a .csv file');
      }
    }
  };

  const handleSubmit = async () => {
    if (!Object.keys(config).length) {
      setFileError('Please provide configuration details');
      return;
    }
    if (sourceType === 'csv') {
      if (!file || fileError) {
        setFileError('Please select a valid CSV file');
        return;
      }
      const formData = new FormData();
      formData.append('file', file);
      try {
        await api.post(`/upload-csv/CELL001`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        onSubmit({ type: sourceType, config });
      } catch (err) {
        setFileError(err.response?.data?.detail || 'Failed to upload CSV');
      }
    } else {
      onSubmit({ type: sourceType, config });
    }
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', borderRadius: 2, boxShadow: 1 }}>
      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>Data Source Type</InputLabel>
        <Select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
          label="Data Source Type"
        >
          <MenuItem value="csv">CSV File</MenuItem>
          <MenuItem value="sql">SQL Database</MenuItem>
          <MenuItem value="google_sheets">Google Sheets</MenuItem>
          <MenuItem value="airtable">Airtable</MenuItem>
          <MenuItem value="api">API</MenuItem>
        </Select>
        <FormHelperText>Select the type of data source to connect</FormHelperText>
      </FormControl>

      {sourceType === 'csv' && (
        <Box sx={{ mb: 2 }}>
          <InputLabel htmlFor="csv-file-upload">Upload CSV File</InputLabel>
          <Input
            id="csv-file-upload"
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            sx={{ mt: 1, mb: 1 }}
          />
          {config.file_path && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected: {config.file_path}
            </Typography>
          )}
          {fileError && (
            <FormHelperText error>{fileError}</FormHelperText>
          )}
          {!fileError && (
            <FormHelperText>Browse and select a .csv file</FormHelperText>
          )}
        </Box>
      )}

      {sourceType === 'sql' && (
        <>
          <TextField
            label="Connection String"
            variant="outlined"
            fullWidth
            value={config.connection_string || ''}
            onChange={(e) => handleConfigChange('connection_string', e.target.value)}
            margin="normal"
            helperText="e.g., postgresql://user:password@host:port/dbname"
            sx={{ mb: 2 }}
          />
          <TextField
            label="SQL Query"
            variant="outlined"
            fullWidth
            value={config.query || ''}
            onChange={(e) => handleConfigChange('query', e.target.value)}
            margin="normal"
            helperText="e.g., SELECT * FROM table_name"
            sx={{ mb: 2 }}
          />
        </>
      )}

      {sourceType === 'google_sheets' && (
        <TextField
          label="Google Sheet ID"
          variant="outlined"
          fullWidth
          value={config.sheet_id || ''}
          onChange={(e) => handleConfigChange('sheet_id', e.target.value)}
          margin="normal"
          helperText="The ID from the Google Sheets URL"
          sx={{ mb: 2 }}
        />
      )}

      {sourceType === 'airtable' && (
        <>
          <TextField
            label="Airtable Base ID"
            variant="outlined"
            fullWidth
            value={config.base_id || ''}
            onChange={(e) => handleConfigChange('base_id', e.target.value)}
            margin="normal"
            helperText="e.g., appXXXXXXXXXXXXXX"
            sx={{ mb: 2 }}
          />
          <TextField
            label="Table Name"
            variant="outlined"
            fullWidth
            value={config.table_name || ''}
            onChange={(e) => handleConfigChange('table_name', e.target.value)}
            margin="normal"
            helperText="Name of the table in Airtable"
            sx={{ mb: 2 }}
          />
        </>
      )}

      {sourceType === 'api' && (
        <>
          <TextField
            label="API URL"
            variant="outlined"
            fullWidth
            value={config.url || ''}
            onChange={(e) => handleConfigChange('url', e.target.value)}
            margin="normal"
            helperText="e.g., https://api.example.com/data"
            sx={{ mb: 2 }}
          />
          <TextField
            label="Data Key (optional)"
            variant="outlined"
            fullWidth
            value={config.data_key || ''}
            onChange={(e) => handleConfigChange('data_key', e.target.value)}
            margin="normal"
            helperText="Key to extract data from API response"
            sx={{ mb: 2 }}
          />
        </>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleSubmit}
        fullWidth
        sx={{ mt: 2, py: 1.5 }}
      >
        Connect
      </Button>
    </Box>
  );
}