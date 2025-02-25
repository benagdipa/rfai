import { useState, useCallback } from 'react';
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
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import api from '../lib/api';

export default function DataSourceConfig({ onSubmit, initialConfig = {} }) {
  const [sourceType, setSourceType] = useState(initialConfig.type || 'csv');
  const [config, setConfig] = useState(initialConfig.config || {});
  const [file, setFile] = useState(null);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState('');

  // Handle changes to configuration fields
  const handleConfigChange = useCallback((key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: '' }));
  }, []);

  // Handle file selection for CSV
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (selectedFile.name.endsWith('.csv')) {
        setFile(selectedFile);
        handleConfigChange('file_path', selectedFile.name);
      } else {
        setErrors((prev) => ({ ...prev, file_path: 'Please select a .csv file' }));
        setFile(null);
      }
    }
  };

  // Validate form fields based on source type
  const validateForm = () => {
    const newErrors = {};
    if (sourceType === 'csv' && !file) {
      newErrors.file_path = 'Please select a valid CSV file';
    } else if (sourceType === 'sql') {
      if (!config.connection_string) newErrors.connection_string = 'Connection string is required';
      if (!config.query) newErrors.query = 'SQL query is required';
    } else if (sourceType === 'google_sheets') {
      if (!config.sheet_id) newErrors.sheet_id = 'Google Sheet ID is required';
    } else if (sourceType === 'airtable') {
      if (!config.base_id) newErrors.base_id = 'Airtable Base ID is required';
      if (!config.table_name) newErrors.table_name = 'Table name is required';
    } else if (sourceType === 'api') {
      if (!config.url) newErrors.url = 'API URL is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async () => {
    if (!validateForm()) return;

    setLoading(true);
    setSubmitError('');

    try {
      if (sourceType === 'csv') {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post('api/upload-csv/CELL001', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        onSubmit({ type: sourceType, config: { ...config, file: file.name }, result: response.data });
      } else {
        const response = await api.post('/ingest/CELL001', { type: sourceType, config });
        onSubmit({ type: sourceType, config, result: response.data });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || `Failed to ${sourceType === 'csv' ? 'upload CSV' : 'connect to data source'}`;
      setSubmitError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', borderRadius: 2, boxShadow: 1 }}>
      {submitError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {submitError}
        </Alert>
      )}

      <FormControl fullWidth sx={{ mb: 3 }}>
        <InputLabel>Data Source Type</InputLabel>
        <Select
          value={sourceType}
          onChange={(e) => {
            setSourceType(e.target.value);
            setConfig({});
            setFile(null);
            setErrors({});
          }}
          label="Data Source Type"
          disabled={loading}
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
            disabled={loading}
            sx={{ mt: 1, mb: 1 }}
          />
          {config.file_path && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected: {config.file_path}
            </Typography>
          )}
          {errors.file_path && (
            <FormHelperText error>{errors.file_path}</FormHelperText>
          )}
          {!errors.file_path && (
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
            error={!!errors.connection_string}
            helperText={errors.connection_string || "e.g., postgresql://user:password@host:port/dbname"}
            disabled={loading}
            sx={{ mb: 2 }}
          />
          <TextField
            label="SQL Query"
            variant="outlined"
            fullWidth
            value={config.query || ''}
            onChange={(e) => handleConfigChange('query', e.target.value)}
            margin="normal"
            error={!!errors.query}
            helperText={errors.query || "e.g., SELECT * FROM table_name"}
            disabled={loading}
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
          error={!!errors.sheet_id}
          helperText={errors.sheet_id || "The ID from the Google Sheets URL"}
          disabled={loading}
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
            error={!!errors.base_id}
            helperText={errors.base_id || "e.g., appXXXXXXXXXXXXXX"}
            disabled={loading}
            sx={{ mb: 2 }}
          />
          <TextField
            label="Table Name"
            variant="outlined"
            fullWidth
            value={config.table_name || ''}
            onChange={(e) => handleConfigChange('table_name', e.target.value)}
            margin="normal"
            error={!!errors.table_name}
            helperText={errors.table_name || "Name of the table in Airtable"}
            disabled={loading}
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
            error={!!errors.url}
            helperText={errors.url || "e.g., https://api.example.com/data"}
            disabled={loading}
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
            disabled={loading}
            sx={{ mb: 2 }}
          />
        </>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleSubmit}
        fullWidth
        disabled={loading}
        sx={{ mt: 2, py: 1.5 }}
        startIcon={loading ? <CircularProgress size={20} /> : null}
      >
        {loading ? 'Connecting...' : 'Connect'}
      </Button>
    </Box>
  );
}