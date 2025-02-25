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
import { NavLink, useNavigate } from 'react-router-dom'; // Assuming React Router
import { logout, getCurrentUser } from '../lib/auth'; // Enhanced auth utilities
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircle from '@mui/icons-material/AccountCircle';

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  boxShadow: theme.shadows[4],
}));

const StyledNavLink = styled(NavLink)(({ theme }) => ({
  color: theme.palette.common.white,
  textDecoration: 'none',
  marginRight: theme.spacing(2),
  '&.active': {
    borderBottom: `2px solid ${theme.palette.secondary.main}`,
  },
  '&:hover': {
    opacity: 0.8,
  },
}));

const Navbar = () => {
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const navigate = useNavigate();

  // Fetch current user on mount
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const currentUser = await getCurrentUser(); // Assumes this fetches user info
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
      await logout(); // Clears token and logs out
      setUser(null);
      navigate('/login');
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
          <StyledNavLink to="/" exact activeClassName="active">
            <Button color="inherit">Home</Button>
          </StyledNavLink>
          <StyledNavLink to="/data" activeClassName="active">
            <Button color="inherit">Data Sources</Button>
          </StyledNavLink>
          <StyledNavLink to="/kpis" activeClassName="active">
            <Button color="inherit">KPIs</Button>
          </StyledNavLink>
          <StyledNavLink to="/map" activeClassName="active">
            <Button color="inherit">Network Map</Button>
          </StyledNavLink>
          <StyledNavLink to="/predictions" activeClassName="active">
            <Button color="inherit">Predictions</Button>
          </StyledNavLink>
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
              <MenuItem onClick={() => navigate('/profile')}>Profile</MenuItem>
              <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
          </Box>
        ) : (
          <Button color="inherit" onClick={() => navigate('/login')}>
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
        <MenuItem onClick={() => navigate('/')}>Home</MenuItem>
        <MenuItem onClick={() => navigate('/data')}>Data Sources</MenuItem>
        <MenuItem onClick={() => navigate('/kpis')}>KPIs</MenuItem>
        <MenuItem onClick={() => navigate('/map')}>Network Map</MenuItem>
        <MenuItem onClick={() => navigate('/predictions')}>Predictions</MenuItem>
      </Menu>
    </StyledAppBar>
  );
};

export default Navbar;