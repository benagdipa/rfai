import React, { useEffect, useMemo } from 'react';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { CircularProgress, Box, Typography, Button } from '@mui/material';
import { store, persistor } from '../store'; // Adjust path
import theme from '../styles/theme'; // Your MUI theme file
import '../styles/globals.css'; // Global styles

// Loading Component for consistent SSR and client rendering
function LoadingComponent() {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <CircularProgress />
      <Typography variant="body1" sx={{ mt: 2 }}>
        Loading...
      </Typography>
    </Box>
  );
}

// Error Boundary for catching runtime errors
function ErrorBoundary({ children }) {
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    const handleError = (event) => {
      console.error('ErrorBoundary caught:', event.error || event.reason);
      setError(event.error || new Error('Unknown error occurred'));
    };
    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleError);
    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleError);
    };
  }, []);

  if (error) {
    return (
      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Typography variant="h6" color="error">
          Something went wrong
        </Typography>
        <Typography variant="body1" sx={{ mt: 1 }}>
          {error.message}
        </Typography>
        <Button variant="contained" onClick={() => window.location.reload()} sx={{ mt: 2 }}>
          Reload
        </Button>
      </Box>
    );
  }
  return children;
}

// App Wrapper with minimal logic
function AppWrapper({ Component, pageProps }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Component {...pageProps} />
    </ThemeProvider>
  );
}

// Main App Component with error logging
function MyApp({ Component, pageProps }) {
  try {
    return (
      <Provider store={store}>
        <ErrorBoundary>
          {typeof window !== 'undefined' ? (
            <PersistGate loading={<LoadingComponent />} persistor={persistor}>
              <AppWrapper Component={Component} pageProps={pageProps} />
            </PersistGate>
          ) : (
            <LoadingComponent />
          )}
        </ErrorBoundary>
      </Provider>
    );
  } catch (error) {
    console.error('MyApp caught error during render:', error);
    throw error; // Re-throw to ensure Next.js captures it
  }
}

export default MyApp;