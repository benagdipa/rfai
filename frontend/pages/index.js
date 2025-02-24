import { Typography, Button, Box } from '@mui/material';
import { useRouter } from 'next/router';

export default function Home() {
  const router = useRouter();

  return (
    <Box sx={{ textAlign: 'center', mt: 8 }}>
      <Typography variant="h4" gutterBottom>Welcome to Network Dashboard</Typography>
      <Button variant="contained" sx={{ mr: 2 }} onClick={() => router.push('/login')}>
        Login
      </Button>
      <Button variant="outlined" onClick={() => router.push('/signup')}>
        Sign Up
      </Button>
    </Box>
  );
}