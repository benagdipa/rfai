import { Provider } from 'react-redux';
import { ThemeProvider } from '@mui/material/styles';
import { store } from '../store';
import ErrorBoundary from '../components/ErrorBoundary';
import Navbar from '../components/Navbar';
import theme from '../styles/theme';
import '../styles/globals.css';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

function MyApp({ Component, pageProps }) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token && router.pathname !== '/login' && router.pathname !== '/signup') {
      router.push('/login');
    }
  }, [router]);

  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <ErrorBoundary>
          <Navbar />
          <Component {...pageProps} />
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>
  );
}

export default MyApp;