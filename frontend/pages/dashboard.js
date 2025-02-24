import { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchKpiData, updateEda } from '../store/kpiSlice';
import KpiChart from '../components/KpiChart';
import NetworkMap from '../components/NetworkMap';
import PredictionChart from '../components/PredictionChart';
import DataSourceConfig from '../components/DataSourceConfig';
import api from '../lib/api';
import { WebSocketClient } from '../lib/websocket';
import {
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Paper,
  Grid,
  Box,
  CircularProgress,
  Tabs,
  Tab,
  Drawer,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Divider,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
} from '@mui/material';
import { styled } from '@mui/system';
import MenuIcon from '@mui/icons-material/Menu';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';

const drawerWidth = 240;

const ContentBox = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.spacing(1),
  boxShadow: theme.shadows[3],
}));

export default function Dashboard() {
  const dispatch = useDispatch();
  const { data, eda, status, error } = useSelector((state) => state.kpi);
  const [wsClient, setWsClient] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const identifier = 'CELL001';

  // Fetch initial data and set up WebSocket connection
  useEffect(() => {
    dispatch(fetchKpiData(identifier));
    const client = new WebSocketClient(process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws', (message) => {
      dispatch(updateEda(message));
    });
    setWsClient(client);
    return () => client.close();
  }, [dispatch]);

  // Handle data source submission
  const handleDataSourceSubmit = async (sourceConfig) => {
    try {
      await api.post(`/ingest/${identifier}`, sourceConfig);
    } catch (err) {
      console.error('Ingestion failed:', err);
    }
  };

  // Handle tab changes
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Toggle drawer open/close state
  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  // Define dashboard sections with labels, content, and tooltips
  const agentSections = [
    {
      label: 'EDA & Insights',
      content: renderEdaInsights,
      tooltip: 'Insights from exploratory data analysis.',
    },
    {
      label: 'Network Map',
      content: renderNetworkMap,
      tooltip: 'Visualizes network status and anomalies.',
    },
    {
      label: 'Predictions',
      content: renderPredictions,
      tooltip: 'Displays predictive analytics for network performance.',
    },
    {
      label: 'Issues & RCA',
      content: renderIssuesRca,
      tooltip: 'Coming soon: Issue detection and root cause analysis.',
    },
    {
      label: 'Optimization',
      content: renderOptimization,
      tooltip: 'Coming soon: AI-driven optimization suggestions.',
    },
  ];

  // Drawer content for navigation
  const drawerContent = (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', p: 1 }}>
        <Typography variant="h6">Dashboard</Typography>
      </Box>
      <Divider sx={{ bgcolor: 'grey.700' }} />
      <List>
        {agentSections.map((section, index) => (
          <ListItem
            button
            key={index}
            onClick={() => {
              setTabValue(index);
              setDrawerOpen(false); // Close temporary drawer on selection
            }}
            sx={{
              bgcolor: tabValue === index ? 'grey.800' : 'transparent',
              '&:hover': { bgcolor: 'grey.700' },
            }}
          >
            <ListItemText primary={section.label} />
          </ListItem>
        ))}
      </List>
    </>
  );

  // Render functions for each tab section
  function renderEdaInsights() {
    return (
      <ContentBox>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Exploratory Data Analysis</Typography>
          <Tooltip title={agentSections[0].tooltip}>
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {status === 'loading' && <CircularProgress />}
        {error && <Typography color="error">{error}</Typography>}
        {eda ? (
          <>
            <Typography variant="body2" color="textSecondary">
              Identifier: {eda.identifier}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Clusters: {eda.clusters}
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              AI Insights: {eda.ai_insights}
            </Typography>
            <KpiChart data={eda} />
          </>
        ) : (
          <Typography>No EDA data available</Typography>
        )}
      </ContentBox>
    );
  }

  function renderNetworkMap() {
    return (
      <ContentBox>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Network Monitoring</Typography>
          <Tooltip title={agentSections[1].tooltip}>
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {data?.monitor ? (
          <>
            <Chip
              label={data.monitor.anomalies_detected ? 'Anomalies Detected' : 'Stable'}
              color={data.monitor.anomalies_detected ? 'error' : 'success'}
              sx={{ mb: 2 }}
            />
            <NetworkMap cells={[data.monitor]} />
          </>
        ) : (
          <Typography>No network data available</Typography>
        )}
      </ContentBox>
    );
  }

  function renderPredictions() {
    return (
      <ContentBox>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Predictive Analytics</Typography>
          <Tooltip title={agentSections[2].tooltip}>
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {data?.predict ? (
          <PredictionChart predictions={data.predict.predictions} />
        ) : (
          <Typography>No predictions available</Typography>
        )}
      </ContentBox>
    );
  }

  function renderIssuesRca() {
    return (
      <ContentBox>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Issues & Root Cause Analysis</Typography>
          <Tooltip title={agentSections[3].tooltip}>
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Typography variant="body2" color="textSecondary">
          Coming soon: Detailed issue detection and root cause analysis.
        </Typography>
      </ContentBox>
    );
  }

  function renderOptimization() {
    return (
      <ContentBox>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Optimization Proposals</Typography>
          <Tooltip title={agentSections[4].tooltip}>
            <IconButton size="small" sx={{ ml: 1 }}>
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        <Typography variant="body2" color="textSecondary">
          Coming soon: AI-driven optimization suggestions.
        </Typography>
      </ContentBox>
    );
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      {/* AppBar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            4G/5G Network Dashboard
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Permanent Drawer for Large Screens */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
            backgroundColor: 'grey.900',
            color: 'common.white',
          },
        }}
        open
      >
        {drawerContent}
      </Drawer>

      {/* Temporary Drawer for Small Screens */}
      <Drawer
        variant="temporary"
        anchor="left"
        open={drawerOpen}
        onClose={handleDrawerToggle}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: drawerWidth,
            backgroundColor: 'grey.900',
            color: 'common.white',
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          ml: { md: `${drawerWidth}px` }, // Fixed margin for large screens
          transition: 'margin-left 0.3s',
        }}
      >
        <Toolbar /> {/* Spacer for fixed AppBar */}
        <Grid container spacing={3}>
          {/* Data Source Config */}
          <Grid item xs={12} md={3}>
            <Paper elevation={3} sx={{ p: 2, height: '100%' }}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">Data Source Configuration</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <DataSourceConfig onSubmit={handleDataSourceSubmit} />
                </AccordionDetails>
              </Accordion>
            </Paper>
          </Grid>

          {/* Main Dashboard Content */}
          <Grid item xs={12} md={9}>
            <Paper elevation={3} sx={{ p: 2 }}>
              <Tabs
                value={tabValue}
                onChange={handleTabChange}
                variant="scrollable"
                scrollButtons="auto"
                sx={{ mb: 2 }}
              >
                {agentSections.map((section, index) => (
                  <Tab key={index} label={section.label} />
                ))}
              </Tabs>
              {agentSections[tabValue].content()}
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
}