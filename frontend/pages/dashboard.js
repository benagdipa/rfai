import { useEffect, useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchKpiData, updateEda, updateDataSection, selectKpiData, selectKpiStatus, selectKpiError } from '../store/kpiSlice';
import KpiChart from '../components/KpiChart';
import PredictionChart from '../components/PredictionChart';
import NetworkMap from '../components/NetworkMap';
import DataSourceConfig from '../components/DataSourceConfig';
import { useWebSocket } from '../lib/websocket';
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
  Alert,
  Badge,
} from '@mui/material';
import { styled } from '@mui/system';
import MenuIcon from '@mui/icons-material/Menu';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';
import dynamic from 'next/dynamic';

// Dynamically import NetworkMap to disable SSR
const NetworkMapDynamic = dynamic(() => import('../components/NetworkMap'), { ssr: false });

const drawerWidth = 240;

const ContentBox = styled(Box)(({ theme }) => ({
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.spacing(1),
  boxShadow: theme.shadows[3],
  minHeight: '300px',
}));

const Dashboard = () => {
  const dispatch = useDispatch();
  const { data, eda, status, error } = useSelector((state) => state.kpi);
  const [tabValue, setTabValue] = useState(0);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [wsError, setWsError] = useState('');
  const identifier = 'CELL001';

  // WebSocket setup using enhanced hook
  const { status: wsStatus, error: wsErrorMsg } = useWebSocket({
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',
    onMessage: (message) => {
      if (message.data.identifier === identifier) {
        switch (message.event_type) {
          case 'eda_complete':
            dispatch(updateEda(message.data));
            break;
          case 'kpis_monitored':
            dispatch(updateDataSection({ section: 'monitor', data: message.data }));
            break;
          case 'predictions_generated':
            dispatch(updateDataSection({ section: 'predict', data: message.data }));
            break;
          case 'issues_detected':
            dispatch(updateDataSection({ section: 'issues', data: message.data }));
            break;
          case 'optimization_proposed':
            dispatch(updateDataSection({ section: 'optimization', data: message.data }));
            break;
          default:
            console.log('Unhandled WebSocket event:', message.event_type);
        }
      }
    },
    onError: (err) => setWsError(err.message),
  });

  // Fetch initial KPI data
  useEffect(() => {
    dispatch(fetchKpiData(identifier));
  }, [dispatch, identifier]);

  // Handle data source submission
  const handleDataSourceSubmit = useCallback(async (sourceConfig) => {
    try {
      await api.post(`/ingest/${identifier}`, sourceConfig);
      console.log('Data source submitted:', sourceConfig);
      // Optionally refetch data after ingestion
      dispatch(fetchKpiData(identifier));
    } catch (err) {
      console.error('Ingestion failed:', err.message);
      setWsError(err.message);
    }
  }, [identifier, dispatch]);

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
      tooltip: 'Issue detection and root cause analysis.',
    },
    {
      label: 'Optimization',
      content: renderOptimization,
      tooltip: 'AI-driven optimization suggestions.',
    },
  ];

  // Drawer content for navigation with badge for issues
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
              setDrawerOpen(false);
            }}
            sx={{
              bgcolor: tabValue === index ? 'grey.800' : 'transparent',
              '&:hover': { bgcolor: 'grey.700' },
            }}
            aria-label={section.label}
          >
            <ListItemText primary={section.label} />
            {section.label === 'Issues & RCA' && data?.issues?.issues?.length > 0 && (
              <Badge badgeContent={data.issues.issues.length} color="error" sx={{ ml: 1 }} />
            )}
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
            <IconButton size="small" sx={{ ml: 1 }} aria-label="EDA info">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {status === 'loading' && <CircularProgress />}
        {error && <Alert severity="error">{error}</Alert>}
        {eda ? (
          <>
            <Typography variant="body2" color="textSecondary">
              Identifier: {eda.identifier}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Clusters: {eda.clusters || 'N/A'}
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              AI Insights: {eda.ai_insights || 'No insights available'}
            </Typography>
            <KpiChart data={eda} identifier={identifier} />
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
            <IconButton size="small" sx={{ ml: 1 }} aria-label="Network info">
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
            <NetworkMapDynamic cells={[data.monitor]} identifier={identifier} />
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
            <IconButton size="small" sx={{ ml: 1 }} aria-label="Predictions info">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {data?.predict ? (
          <PredictionChart predictions={data.predict.predictions} identifier={identifier} />
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
            <IconButton size="small" sx={{ ml: 1 }} aria-label="Issues info">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {data?.issues?.issues ? (
          <>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Detected Issues: {data.issues.issues.length}
            </Typography>
            {data.issues.issues.map((issue, index) => (
              <Accordion key={index}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle2">{issue.description}</Typography>
                  <Chip
                    label={issue.severity}
                    color={issue.severity === 'critical' ? 'error' : 'warning'}
                    size="small"
                    sx={{ ml: 1 }}
                  />
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2">
                    Status: {issue.status} <br />
                    Detected At: {new Date(issue.detected_at).toLocaleString()} <br />
                    {issue.resolved_at && `Resolved At: ${new Date(issue.resolved_at).toLocaleString()}`}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </>
        ) : (
          <Typography>No issues detected</Typography>
        )}
      </ContentBox>
    );
  }

  function renderOptimization() {
    return (
      <ContentBox>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Optimization Proposals</Typography>
          <Tooltip title={agentSections[4].tooltip}>
            <IconButton size="small" sx={{ ml: 1 }} aria-label="Optimization info">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
        {data?.optimization?.proposals ? (
          <>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              Proposals: {data.optimization.proposals.length}
            </Typography>
            {data.optimization.proposals.map((proposal, index) => (
              <Accordion key={index}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle2">{proposal.description}</Typography>
                  <Chip
                    label={`${(proposal.confidence * 100).toFixed(0)}%`}
                    color={proposal.is_actionable ? 'primary' : 'default'}
                    size="small"
                    sx={{ ml: 1 }}
                  />
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2">
                    Status: {proposal.status} <br />
                    Created At: {new Date(proposal.created_at).toLocaleString()} <br />
                    {proposal.implemented_at && `Implemented At: ${new Date(proposal.implemented_at).toLocaleString()}`}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </>
        ) : (
          <Typography>No optimization proposals available</Typography>
        )}
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
          zIndex: (theme) => theme.zIndex.drawer + 1,
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
          <Box sx={{ flexGrow: 1 }} />
          {wsStatus.isConnected ? (
            <Chip label="Connected" color="success" size="small" sx={{ ml: 2 }} />
          ) : (
            <Chip label="Disconnected" color="error" size="small" sx={{ ml: 2 }} />
          )}
          {wsError && (
            <Tooltip title={wsError}>
              <Chip label="WebSocket Error" color="error" size="small" sx={{ ml: 1 }} />
            </Tooltip>
          )}
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
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          transition: 'margin-left 0.3s',
        }}
      >
        <Toolbar /> {/* Spacer for fixed AppBar */}
        <Grid container spacing={3}>
          {/* Data Source Config */}
          <Grid item xs={12} md={3}>
            <Paper elevation={3} sx={{ p: 2, height: '100%' }}>
              <Accordion defaultExpanded>
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
                aria-label="Dashboard sections"
              >
                {agentSections.map((section, index) => (
                  <Tab key={index} label={section.label} aria-label={section.label} />
                ))}
              </Tabs>
              {agentSections[tabValue].content()}
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
};

export default Dashboard;