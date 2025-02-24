import { useState } from 'react';
import { useRouter } from 'next/router';
import { login } from '../lib/auth';
import { TextField, Button, Typography, Box, Link as MuiLink } from '@mui/material';
import Link from 'next/link';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please fill in all fields');
      return;
    }
    try {
      await login(username, password);
      router.push('/dashboard');
    } catch (err) {
      let errorMessage = 'Login failed';
      if (err.response?.data) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          // Handle validation errors like [{"loc": ..., "msg": ..., "type": ...}]
          errorMessage = err.response.data.detail.map(e => e.msg).join(', ');
        } else {
          errorMessage = 'An unexpected error occurred';
        }
      }
      setError(errorMessage);
    }
  };

  return (
    <Box
      sx={{
        maxWidth: 400,
        mx: 'auto',
        mt: 8,
        p: 4,
        boxShadow: 3,
        borderRadius: 2,
        bgcolor: 'background.paper',
      }}
    >
      <Typography variant="h4" align="center" gutterBottom>
        Login
      </Typography>
      <form onSubmit={handleSubmit}>
        <TextField
          label="Username"
          variant="outlined"
          fullWidth
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          margin="normal"
          required
          autoFocus
        />
        <TextField
          label="Password"
          type="password"
          variant="outlined"
          fullWidth
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          margin="normal"
          required
        />
        <Button
          type="submit"
          variant="contained"
          color="primary"
          fullWidth
          sx={{ mt: 2, py: 1.5 }}
        >
          Login
        </Button>
      </form>
      {error && (
        <Typography color="error" align="center" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}
      <Typography align="center" sx={{ mt: 2 }}>
        Don’t have an account?{' '}
        <MuiLink component={Link} href="/signup" underline="hover">
          Register here
        </MuiLink>
      </Typography>
    </Box>
  );
}