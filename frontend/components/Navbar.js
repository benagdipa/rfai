import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
  Tooltip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { useRouter } from 'next/router'; // Replace react-router-dom with Next.js router
import Link from 'next/link'; // Replace NavLink with Next.js Link
import { logout, getCurrentUser } from '../lib/auth';
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircle from '@mui/icons-material/AccountCircle';

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  boxShadow: theme.shadows[4],
}));

const StyledLink = styled(Link)(({ theme }) => ({
  color: theme.palette.common.white,
  textDecoration: 'none',
  marginRight: theme.spacing(2),
  '& .active': {
    borderBottom: `2px solid ${theme.palette.secondary.main}`,
  },
  '&:hover': {
    opacity: 0.8,
  },
}));

const Navbar = () => {
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const router = useRouter();

  // Fetch current user on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch (err) {
        console.error('Failed to fetch user:', err);
        setUser(null);
      }
    };
    fetchUser();
  }, []);

  // Handle menu open/close
  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  // Enhanced logout with navigation
  const handleLogout = async () => {
    try {
      await logout(() => router.push('/login')); // Pass router.push as navigate
      setUser(null);
    } catch (err) {
      console.error('Logout failed:', err);
    }
    handleMenuClose();
  };

  const isMenuOpen = Boolean(anchorEl);

  return (
    <StyledAppBar position="static">
      <Toolbar>
        {/* Responsive menu icon for small screens */}
        <IconButton
          edge="start"
          color="inherit"
          aria-label="menu"
          onClick={handleMenuOpen}
          sx={{ mr: 2, display: { md: 'none' } }}
        >
          <MenuIcon />
        </IconButton>

        {/* Title */}
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Network Dashboard
        </Typography>

        {/* Navigation links for larger screens */}
        <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
          <StyledLink href="/" passHref>
            <Button color="inherit" className={router.pathname === '/' ? 'active' : ''}>
              Home
            </Button>
          </StyledLink>
          <StyledLink href="/data" passHref>
            <Button color="inherit" className={router.pathname === '/data' ? 'active' : ''}>
              Data Sources
            </Button>
          </StyledLink>
          <StyledLink href="/kpis" passHref>
            <Button color="inherit" className={router.pathname === '/kpis' ? 'active' : ''}>
              KPIs
            </Button>
          </StyledLink>
          <StyledLink href="/map" passHref>
            <Button color="inherit" className={router.pathname === '/map' ? 'active' : ''}>
              Network Map
            </Button>
          </StyledLink>
          <StyledLink href="/predictions" passHref>
            <Button color="inherit" className={router.pathname === '/predictions' ? 'active' : ''}>
              Predictions
            </Button>
          </StyledLink>
        </Box>

        {/* User menu */}
        {user ? (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Tooltip title={user.username || 'User'}>
              <IconButton
                edge="end"
                color="inherit"
                onClick={handleMenuOpen}
                aria-controls="user-menu"
                aria-haspopup="true"
              >
                <Avatar sx={{ width: 32, height: 32 }}>
                  {user.username ? user.username[0].toUpperCase() : <AccountCircle />}
                </Avatar>
              </IconButton>
            </Tooltip>
            <Menu
              id="user-menu"
              anchorEl={anchorEl}
              open={isMenuOpen}
              onClose={handleMenuClose}
              anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
              transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            >
              <MenuItem disabled>{user.username || 'User'}</MenuItem>
              <MenuItem onClick={() => router.push('/profile')}>Profile</MenuItem>
              <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
          </Box>
        ) : (
          <Button color="inherit" onClick={() => router.push('/login')}>
            Login
          </Button>
        )}
      </Toolbar>

      {/* Responsive menu for small screens */}
      <Menu
        anchorEl={anchorEl}
        open={isMenuOpen && !user} // Only show this menu if no user (hamburger menu)
        onClose={handleMenuClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        sx={{ display: { md: 'none' } }}
      >
        <MenuItem onClick={() => router.push('/')}>Home</MenuItem>
        <MenuItem onClick={() => router.push('/data')}>Data Sources</MenuItem>
        <MenuItem onClick={() => router.push('/kpis')}>KPIs</MenuItem>
        <MenuItem onClick={() => router.push('/map')}>Network Map</MenuItem>
        <MenuItem onClick={() => router.push('/predictions')}>Predictions</MenuItem>
      </Menu>
    </StyledAppBar>
  );
};

export default Navbar;