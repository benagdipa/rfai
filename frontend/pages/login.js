import { useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth'; // Enhanced auth hook
import {
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Link as MuiLink,
  CircularProgress,
  InputAdornment,
  IconButton,
} from '@mui/material';
import Link from 'next/link';
import { styled } from '@mui/material/styles';
import { motion } from 'framer-motion'; // For animations
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const LoginBox = styled(Box)(({ theme }) => ({
  maxWidth: 400,
  margin: 'auto',
  marginTop: theme.spacing(8),
  padding: theme.spacing(4),
  boxShadow: theme.shadows[3],
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
}));

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();
  const { login, loading } = useAuth(); // Use enhanced auth hook

  // Handle form submission
  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setError('');

      if (!username || !password) {
        setError('Please fill in all fields');
        return;
      }

      try {
        await login(username, password);
        router.push('/dashboard');
      } catch (err) {
        const errorMessage = err.message || 'Login failed';
        setError(errorMessage);
        console.error('Login error:', {
          message: err.message,
          status: err.response?.status,
          data: err.response?.data,
        });
      }
    },
    [username, password, login, router]
  );

  // Toggle password visibility
  const handleTogglePassword = () => {
    setShowPassword((prev) => !prev);
  };

  // Animation variants
  const fadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={fadeIn}
      transition={{ duration: 0.8 }}
    >
      <LoginBox>
        <Typography variant="h4" align="center" gutterBottom color="primary">
          Login
        </Typography>
        <Typography variant="body2" align="center" color="textSecondary" sx={{ mb: 3 }}>
          Sign in to access your network dashboard
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}
        <form onSubmit={handleSubmit} noValidate>
          <TextField
            label="Username"
            variant="outlined"
            fullWidth
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            margin="normal"
            required
            autoFocus
            disabled={loading}
            aria-label="Username input"
            inputProps={{ maxLength: 20 }} // Align with backend validation
            error={!username && error.includes('username')}
            helperText={!username && error.includes('username') ? 'Username is required' : ''}
          />
          <TextField
            label="Password"
            type={showPassword ? 'text' : 'password'}
            variant="outlined"
            fullWidth
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            margin="normal"
            required
            disabled={loading}
            aria-label="Password input"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={handleTogglePassword}
                    edge="end"
                    aria-label="Toggle password visibility"
                    disabled={loading}
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
            error={!password && error.includes('password')}
            helperText={!password && error.includes('password') ? 'Password is required' : ''}
          />
          <Button
            type="submit"
            variant="contained"
            color="primary"
            fullWidth
            sx={{ mt: 3, py: 1.5 }}
            disabled={loading}
            aria-label="Login button"
          >
            {loading ? <CircularProgress size={24} /> : 'Login'}
          </Button>
        </form>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="textSecondary">
            Don’t have an account?{' '}
            <MuiLink
              component={Link}
              href="/signup"
              underline="hover"
              aria-label="Sign up link"
            >
              Register here
            </MuiLink>
          </Typography>
        </Box>
      </LoginBox>
    </motion.div>
  );
};

export default Login;