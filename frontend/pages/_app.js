import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { ThemeProvider, CssBaseline } from '@mui/material/styles';
import { store, persistor } from '../store'; // Enhanced store with persistence
import ErrorBoundary from '../components/ErrorBoundary';
import Navbar from '../components/Navbar';
import theme from '../styles/theme'; // Base theme
import '../styles/globals.css';
import { useAuth } from '../lib/auth'; // Enhanced auth hook
import { useSelector, useDispatch } from 'react-redux';
import { setThemeMode } from '../store/uiSlice'; // UI state management
import {
  Box,
  CircularProgress,
  Typography,
  Snackbar,
  Alert as MuiAlert,
} from '@mui/material';
import { createTheme, responsiveFontSizes } from '@mui/material/styles';

// Protected routes requiring authentication
const protectedRoutes = ['/', '/dashboard', '/data', '/kpis', '/map', '/predictions', '/profile'];

function MyApp({ Component, pageProps }) {
  const router = useRouter();
  const dispatch = useDispatch();
  const [isLoading, setIsLoading] = useState(true); // Track initial auth loading
  const { user, loading: authLoading } = useAuth(); // Use enhanced auth hook
  const { themeMode, notifications } = useSelector((state) => state.ui); // UI state

  // Dynamic theme based on uiSlice themeMode
  const appliedTheme = responsiveFontSizes(
    createTheme({
      ...theme,
      palette: {
        ...theme.palette,
        mode: themeMode || 'light', // Sync with uiSlice
      },
    })
  );

  // Authentication check and redirect
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      try {
        if (!user && protectedRoutes.includes(router.pathname)) {
          router.push('/login');
        } else if (user && (router.pathname === '/login' || router.pathname === '/signup')) {
          router.push('/dashboard'); // Redirect logged-in users to dashboard
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        router.push('/login');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [router, user]);

  // Custom layout for pages
  const getLayout = Component.getLayout || ((page) => page);

  // Handle notification close
  const handleCloseNotification = (id) => {
    dispatch({ type: 'ui/removeNotification', payload: id });
  };

  // Render loading state during initial auth check or persistence
  if (isLoading || authLoading) {
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

  return (
    <Provider store={store}>
      <PersistGate loading={<div>Loading persisted state...</div>} persistor={persistor}>
        <ThemeProvider theme={appliedTheme}>
          <CssBaseline />
          <ErrorBoundary
            fallback={
              <Box sx={{ textAlign: 'center', mt: 4 }}>
                <Typography variant="h6" color="error">
                  An error occurred
                </Typography>
                <Typography variant="body1" sx={{ mt: 1 }}>
                  Please try refreshing the page or contact support.
                </Typography>
                <Button variant="contained" onClick={() => router.reload()} sx={{ mt: 2 }}>
                  Refresh
                </Button>
              </Box>
            }
          >
            <Navbar /> {/* Navbar uses useAuth internally */}
            {getLayout(<Component {...pageProps} user={user} />)}
            {/* Global notifications */}
            {notifications.map((notification) => (
              <Snackbar
                key={notification.id}
                open
                autoHideDuration={6000}
                onClose={() => handleCloseNotification(notification.id)}
                anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
              >
                <MuiAlert
                  onClose={() => handleCloseNotification(notification.id)}
                  severity={notification.severity}
                  sx={{ width: '100%' }}
                >
                  {notification.message}
                </MuiAlert>
              </Snackbar>
            ))}
          </ErrorBoundary>
        </ThemeProvider>
      </PersistGate>
    </Provider>
  );
}

// Add getInitialProps for page-specific props
MyApp.getInitialProps = async ({ Component, ctx }) => {
  let pageProps = {};
  if (Component.getInitialProps) {
    pageProps = await Component.getInitialProps(ctx);
  }
  return { pageProps };
};

export default MyApp;