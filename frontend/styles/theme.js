import { createTheme } from '@mui/material/styles';

// Base theme configuration (light mode by default)
const baseTheme = {
  palette: {
    primary: {
      main: '#1976d2', // Matches globals.css --primary-main
      light: '#4791db',
      dark: '#115293',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#dc004e', // Matches globals.css --secondary-main (adjusted for consistency)
      light: '#e33371',
      dark: '#9a0036',
      contrastText: '#ffffff',
    },
    error: {
      main: '#d32f2f', // Matches globals.css --error-main
      light: '#ef5350',
      dark: '#c62828',
    },
    success: {
      main: '#2e7d32', // Matches globals.css --success-main
      light: '#4caf50',
      dark: '#1b5e20',
    },
    background: {
      default: '#f0f2f5', // Matches globals.css --background-default (light mode)
      paper: '#ffffff', // Matches globals.css --background-paper (light mode)
    },
    text: {
      primary: '#212121', // Matches globals.css --text-primary (light mode)
      secondary: '#757575', // Matches globals.css --text-secondary (light mode)
    },
    mode: 'light', // Default mode, overridden in _app.js
  },
  typography: {
    fontFamily: 'Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif',
    h4: {
      fontSize: '2rem',
      fontWeight: 500,
      '@media (max-width:600px)': {
        fontSize: '1.5rem', // Responsive adjustment
      },
    },
    h6: {
      fontSize: '1.25rem',
      fontWeight: 500,
      '@media (max-width:600px)': {
        fontSize: '1.1rem',
      },
    },
    body1: {
      fontSize: '1rem',
      '@media (max-width:600px)': {
        fontSize: '0.9rem',
      },
    },
    body2: {
      fontSize: '0.875rem',
      '@media (max-width:600px)': {
        fontSize: '0.8rem',
      },
    },
  },
  components: {
    // Custom overrides for MUI components
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: 'var(--background-paper)', // Sync with CSS variables
          transition: 'background-color 0.3s ease',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none', // Avoid all-caps by default
          padding: '8px 16px',
        },
        containedPrimary: {
          '&:hover': {
            backgroundColor: '#115293', // Darker shade of primary.main
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: '4px', // Softer edges
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#1e1e1e', // Darker for dark mode drawer
          color: '#ffffff',
        },
      },
    },
  },
  shape: {
    borderRadius: 8, // Consistent rounded corners
  },
  transitions: {
    duration: {
      enteringScreen: 300,
      leavingScreen: 200,
    },
  },
};

// Create the theme (light mode by default, dynamically adjusted in _app.js)
const theme = createTheme(baseTheme);

// Export for use in _app.js
export default theme;