import React from 'react';
import { Typography } from '@mui/material';

class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error('Error:', error, info);
  }

  render() {
    if (this.state.hasError) return <Typography>Something went wrong.</Typography>;
    return this.props.children;
  }
}

export default ErrorBoundary;
