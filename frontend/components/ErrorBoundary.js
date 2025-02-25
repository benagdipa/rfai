import React, { useCallback } from 'react';
import {
  Typography,
  Button,
  Box,
  Alert,
  Divider,
  Collapse,
} from '@mui/material';
import api from '../lib/api'; // Assuming api client for logging to backend
import { styled } from '@mui/material/styles';

const ErrorContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[4],
  maxWidth: 600,
  margin: 'auto',
  marginTop: theme.spacing(4),
}));

class ErrorBoundary extends React.Component {
  state = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  static getDerivedStateFromError(error) {
    // Update state so the next render shows the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details to console and backend
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
    this.logErrorToBackend(error, errorInfo);
  }

  logErrorToBackend = async (error, errorInfo) => {
    try {
      // Send error to backend for logging (assumes an endpoint like /log-error)
      await api.post('/log-error', {
        error: {
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          timestamp: new Date().toISOString(),
          location: typeof window!=='undefined' ?window.location.href:'',
      
        },
      });
    } catch (err) {
      console.error('Failed to log error to backend:', err);
    }
  };

  handleReset = () => {
    // Reset state to attempt recovery
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    const { hasError, error, errorInfo, showDetails } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      const errorMessage = error?.message || 'An unexpected error occurred';
      const errorDetails = errorInfo?.componentStack || 'No component stack available';

      return (
        <ErrorContainer>
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="h6">Something Went Wrong</Typography>
            <Typography variant="body1">{errorMessage}</Typography>
          </Alert>

          <Button
            variant="outlined"
            color="primary"
            onClick={this.toggleDetails}
            sx={{ mb: 2 }}
          >
            {showDetails ? 'Hide Details' : 'Show Details'}
          </Button>

          <Collapse in={showDetails}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" color="textSecondary">
                Error Details:
              </Typography>
              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                {error?.stack || errorMessage}
              </Typography>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2" color="textSecondary">
                Component Stack:
              </Typography>
              <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                {errorDetails}
              </Typography>
            </Box>
          </Collapse>

          <Button
            variant="contained"
            color="primary"
            onClick={this.handleReset}
            fullWidth
          >
            Try Again
          </Button>

          {fallback && (
            <Box sx={{ mt: 2 }}>
              <Divider sx={{ my: 1 }} />
              {fallback}
            </Box>
          )}
        </ErrorContainer>
      );
    }

    return children;
  }
}

export default ErrorBoundary;

// Functional component wrapper for Hooks usage (optional)
export function ErrorBoundaryWrapper({ children, fallback }) {
  const handleErrorReset = useCallback(() => {
    // Additional reset logic if needed (e.g., state reset in parent)
    console.log('Error reset triggered');
  }, []);

  return (
    <ErrorBoundary fallback={fallback} onReset={handleErrorReset}>
      {children}
    </ErrorBoundary>
  );
}