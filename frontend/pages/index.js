import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth'; // Enhanced auth hook
import {
  Typography,
  Button,
  Box,
  Container,
  Paper,
  Fade,
  Divider,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion'; // For animations

const WelcomeBox = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[5],
  textAlign: 'center',
  maxWidth: 600,
  margin: 'auto',
  mt: 8,
}));

const Home = () => {
  const router = useRouter();
  const { user, loading } = useAuth(); // Use enhanced auth hook

  // Redirect authenticated users to dashboard
  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  // Handle navigation
  const handleLogin = () => router.push('/login');
  const handleSignup = () => router.push('/signup');
  const handleExplore = () => router.push('/dashboard');

  // Animation variants
  const fadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography variant="body1">Loading...</Typography>
      </Box>
    );
  }

  return (
    <Container>
      <motion.div
        initial="hidden"
        animate="visible"
        variants={fadeIn}
        transition={{ duration: 0.8 }}
      >
        <WelcomeBox elevation={3}>
          <Typography variant="h4" gutterBottom color="primary">
            Welcome to the Network Dashboard
          </Typography>
          <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
            Monitor, analyze, and optimize your 4G/5G network with real-time insights and AI-driven predictions.
          </Typography>
          <Divider sx={{ mb: 3 }} />
          {user ? (
            <Box>
              <Typography variant="h6" gutterBottom>
                Hello, {user.username}!
              </Typography>
              <Button
                variant="contained"
                color="primary"
                onClick={handleExplore}
                sx={{ mt: 2, px: 4, py: 1.5 }}
                aria-label="Go to Dashboard"
              >
                Go to Dashboard
              </Button>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleLogin}
                sx={{ px: 4, py: 1.5 }}
                aria-label="Login"
              >
                Login
              </Button>
              <Button
                variant="outlined"
                color="primary"
                onClick={handleSignup}
                sx={{ px: 4, py: 1.5 }}
                aria-label="Sign Up"
              >
                Sign Up
              </Button>
            </Box>
          )}
        </WelcomeBox>
      </motion.div>
    </Container>
  );
};

export default Home;