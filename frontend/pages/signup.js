import { useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
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
import { motion } from 'framer-motion';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const SignupBox = styled(Box)(({ theme }) => ({
  maxWidth: 400,
  margin: 'auto',
  marginTop: theme.spacing(8),
  padding: theme.spacing(4),
  boxShadow: theme.shadows[3],
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
}));

const Signup = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const router = useRouter();
  const { signup, loading } = useAuth();

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setError('');

      if (!username || !password || !confirmPassword) {
        setError('Please fill in all fields');
        return;
      }
      if (!/^[a-zA-Z0-9_]{3,20}$/.test(username)) {
        setError('Username must be 3-20 alphanumeric characters or underscores');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (password.length < 8 || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
        setError('Password must be at least 8 characters with an uppercase letter and a number');
        return;
      }

      try {
        await signup(username, password);
        router.push('/dashboard');
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message || 'Signup failed';
        setError(errorMessage);
        console.error('Signup error:', JSON.stringify({
          message: err.message,
          status: err.response?.status,
          data: err.response?.data,
        }, null, 2));
      }
    },
    [username, password, confirmPassword, signup, router]
  );

  const handleTogglePassword = () => setShowPassword((prev) => !prev);
  const handleToggleConfirmPassword = () => setShowConfirmPassword((prev) => !prev);

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
      <SignupBox>
        <Typography variant="h4" align="center" gutterBottom color="primary">
          Sign Up
        </Typography>
        <Typography variant="body2" align="center" color="textSecondary" sx={{ mb: 3 }}>
          Create an account to manage your network dashboard
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
            inputProps={{ maxLength: 20 }}
            error={!username && error.includes('fields')}
            helperText={!username && error.includes('fields') ? 'Username is required' : ''}
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
            error={
              (!password && error.includes('fields')) ||
              (password && error.includes('Password must'))
            }
            helperText={
              !password && error.includes('fields')
                ? 'Password is required'
                : 'Min 8 chars, 1 uppercase, 1 number'
            }
          />
          <TextField
            label="Confirm Password"
            type={showConfirmPassword ? 'text' : 'password'}
            variant="outlined"
            fullWidth
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            margin="normal"
            required
            disabled={loading}
            aria-label="Confirm password input"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={handleToggleConfirmPassword}
                    edge="end"
                    aria-label="Toggle confirm password visibility"
                    disabled={loading}
                  >
                    {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
            error={
              (!confirmPassword && error.includes('fields')) ||
              (confirmPassword && error.includes('match'))
            }
            helperText={
              !confirmPassword && error.includes('fields')
                ? 'Confirm password is required'
                : password !== confirmPassword && confirmPassword
                ? 'Passwords do not match'
                : ''
            }
          />
          <Button
            type="submit"
            variant="contained"
            color="primary"
            fullWidth
            sx={{ mt: 3, py: 1.5 }}
            disabled={loading}
            aria-label="Sign up button"
          >
            {loading ? <CircularProgress size={24} /> : 'Sign Up'}
          </Button>
        </form>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Typography variant="body2" color="textSecondary">
            Already have an account?{' '}
            <MuiLink
              component={Link}
              href="/login"
              underline="hover"
              aria-label="Login link"
            >
              Login here
            </MuiLink>
          </Typography>
        </Box>
      </SignupBox>
    </motion.div>
  );
};

export default Signup;