import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Container, Grid, Paper, Typography, Button, Card, CardContent,
  LinearProgress, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  Alert, CircularProgress, Tab, Tabs, TextField
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { styled } from '@mui/material/styles';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import GetAppIcon from '@mui/icons-material/GetApp';
import RefreshIcon from '@mui/icons-material/Refresh';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  borderRadius: theme.spacing(2),
  boxShadow: '0 4px 20px 0 rgba(0,0,0,0.1)',
}));

const MetricCard = styled(Card)(({ theme }) => ({
  textAlign: 'center',
  borderRadius: theme.spacing(2),
  '& .MuiCardContent-root': {
    padding: theme.spacing(3),
  },
}));

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [deployDialog, setDeployDialog] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(5000);
  const [credentialsForm, setCredentialsForm] = useState({
    app_id: '',
    access_token: '',
    account_id: '',
  });
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [credentialMessage, setCredentialMessage] = useState('');

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/dashboard`);
      const data = await response.json();
      setDashboardData(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
      setLoading(false);
    }
  }, []);

  // Polling
  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchDashboard, refreshInterval]);

  // Deploy handler
  const handleDeploy = async () => {
    setDeploying(true);
    try {
      const response = await fetch(`${API_BASE}/deploy`, { method: 'POST' });
      const data = await response.json();
      alert('Deployment initiated! Check status below.');
      setDeployDialog(false);
      fetchDashboard();
    } catch (error) {
      alert('Deployment failed: ' + error.message);
    } finally {
      setDeploying(false);
    }
  };

  // Save credentials handler
  const handleSaveCredentials = async () => {
    if (!credentialsForm.app_id || !credentialsForm.access_token || !credentialsForm.account_id) {
      setCredentialMessage('All fields are required');
      return;
    }
    
    setSavingCredentials(true);
    setCredentialMessage('');
    try {
      const response = await fetch(`${API_BASE}/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentialsForm),
      });
      const data = await response.json();
      if (response.ok) {
        setCredentialMessage('✅ Credentials saved successfully!');
        setCredentialsForm({ app_id: '', access_token: '', account_id: '' });
        setTimeout(() => setCredentialMessage(''), 3000);
      } else {
        setCredentialMessage('❌ Failed to save: ' + data.error);
      }
    } catch (error) {
      setCredentialMessage('❌ Error: ' + error.message);
    } finally {
      setSavingCredentials(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const status = dashboardData?.status || {};
  const trades = dashboardData?.trades || {};
  const alerts = dashboardData?.alerts || { alerts: [] };
  const metrics = trades.metrics || {};
  const chartData = dashboardData?.chart_data || {};
  
  // V3 Data
  const v3Data = dashboardData?.v3_data || {};
  const v3Monitor = dashboardData?.v3_monitor || {};
  const v3Enabled = v3Data.enabled || false;
  const v3Metrics = v3Data.portfolio_metrics || {};
  const v3Strategies = v3Data.strategies || {};

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f5f5f5', py: 4 }}>
      <Container maxWidth="lg">
        {/* Header */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" sx={{ fontWeight: 'bold', mb: 1 }}>
            Trading AI {v3Enabled ? 'V3' : 'V2'} Dashboard
          </Typography>
          <Typography variant="subtitle1" color="textSecondary">
            {v3Enabled 
              ? 'Multi-Strategy Portfolio: EUR/USD, GBP/USD, USD/JPY'
              : 'Real-time monitoring and control for EUR/USD breakout strategy'}
          </Typography>
          {v3Enabled && (
            <Chip label="V3 MONEY PRINTER 🚀" color="success" sx={{ mt: 1 }} />
          )}
        </Box>

        {/* Alerts */}
        {alerts.alerts && alerts.alerts.length > 0 && (
          <Box sx={{ mb: 3 }}>
            {alerts.alerts.map((alert, idx) => (
              <Alert
                key={idx}
                severity={alert.level === 'CRITICAL' ? 'error' : 'warning'}
                icon={alert.level === 'CRITICAL' ? <ErrorIcon /> : <WarningIcon />}
                sx={{ mb: 1 }}
              >
                {alert.message}
              </Alert>
            ))}
          </Box>
        )}

        {/* Status Overview */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Deployment Status
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                  {status.deployment_status === 'DEPLOYED' && (
                    <CheckCircleIcon sx={{ color: 'green', fontSize: 30 }} />
                  )}
                  <Typography variant="h6">
                    {status.deployment_status || 'NOT_DEPLOYED'}
                  </Typography>
                </Box>
              </CardContent>
            </MetricCard>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <MetricCard>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {v3Enabled ? 'Current Capital' : 'Current Equity'}
                </Typography>
                <Typography variant="h5" sx={{ color: (v3Enabled ? v3Metrics.current_capital : metrics.current_equity) >= (v3Enabled ? 500 : 10000) ? 'green' : 'red' }}>
                  ${v3Enabled ? v3Metrics.current_capital?.toFixed(2) : metrics.current_equity?.toFixed(2)}
                </Typography>
                {v3Enabled && (
                  <Typography variant="caption" color="green">
                    ROI: {v3Metrics.roi?.toFixed(1)}%
                  </Typography>
                )}
                {!v3Enabled && (
                  <Typography variant="caption" color={metrics.current_profit >= 0 ? 'green' : 'red'}>
                    {metrics.current_profit >= 0 ? '+' : ''}{metrics.current_profit?.toFixed(2)}
                  </Typography>
                )}
              </CardContent>
            </MetricCard>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <MetricCard>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  {v3Enabled ? 'Total Value' : 'Max Drawdown'}
                </Typography>
                {v3Enabled ? (
                  <>
                    <Typography variant="h6" sx={{ color: 'green' }}>
                      ${v3Metrics.total_value?.toFixed(0)}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      ${v3Metrics.total_withdrawn?.toFixed(0)} withdrawn
                    </Typography>
                  </>
                ) : (
                  <>
                    <Typography variant="h6" sx={{ color: metrics.max_drawdown > 3000 ? 'red' : 'orange' }}>
                      ${metrics.max_drawdown?.toFixed(0)}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={(metrics.max_drawdown / 3000) * 100}
                      sx={{ mt: 1 }}
                    />
                  </>
                )}
              </CardContent>
            </MetricCard>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <MetricCard>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Win Rate
                </Typography>
                <Typography variant="h5" sx={{ color: (v3Enabled ? v3Metrics.win_rate : metrics.win_rate) >= (v3Enabled ? 70 : 12) ? 'green' : 'orange' }}>
                  {v3Enabled ? v3Metrics.win_rate?.toFixed(1) : metrics.win_rate?.toFixed(1)}%
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {v3Enabled ? v3Metrics.wins : metrics.wins} wins / {v3Enabled ? v3Metrics.losses : metrics.losses} losses
                </Typography>
              </CardContent>
            </MetricCard>
          </Grid>
        </Grid>

        {/* V3 Strategy Breakdown */}
        {v3Enabled && Object.keys(v3Strategies).length > 0 && (
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {Object.entries(v3Strategies).map(([strategyName, strategyData]) => (
              <Grid item xs={12} sm={4} key={strategyName}>
                <StyledPaper>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    {strategyName}
                  </Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Trades</Typography>
                      <Typography variant="h6">{strategyData.trades}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Win Rate</Typography>
                      <Typography variant="h6" sx={{ color: strategyData.win_rate >= 70 ? 'green' : 'orange' }}>
                        {strategyData.win_rate}%
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Wins</Typography>
                      <Typography>{strategyData.wins}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Profit</Typography>
                      <Typography sx={{ color: strategyData.profit >= 0 ? 'green' : 'red' }}>
                        ${strategyData.profit}
                      </Typography>
                    </Box>
                  </Box>
                </StyledPaper>
              </Grid>
            ))}
          </Grid>
        )}

        {/* Tabs */}
        <StyledPaper>
          <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
            <Tab label="Overview" />
            <Tab label="Trades" />
            <Tab label="Charts" />
            {v3Enabled && <Tab label="V3 Monitor" />}
            <Tab label="Settings" />
          </Tabs>

          {/* Tab 0: Overview */}
          {tabValue === 0 && (
            <Box sx={{ p: 3 }}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" sx={{ mb: 2 }}>Key Metrics</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                    <Box>
                      <Typography variant="caption" color="textSecondary">Total Trades</Typography>
                      <Typography variant="h6">{v3Enabled ? v3Metrics.total_trades : metrics.total_trades}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="textSecondary">
                        {v3Enabled ? 'Sharpe Ratio' : 'Profit Factor'}
                      </Typography>
                      <Typography variant="h6" sx={{ color: (v3Enabled ? v3Metrics.sharpe_ratio : metrics.profit_factor) >= (v3Enabled ? 2.0 : 1.8) ? 'green' : 'orange' }}>
                        {v3Enabled ? v3Metrics.sharpe_ratio?.toFixed(2) : metrics.profit_factor?.toFixed(2)}
                      </Typography>
                    </Box>
                    {v3Enabled && (
                      <>
                        <Box>
                          <Typography variant="caption" color="textSecondary">Strategies</Typography>
                          <Typography variant="h6">{Object.keys(v3Strategies).length}</Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="textSecondary">Position Multiplier</Typography>
                          <Typography variant="h6">
                            {(v3Metrics.current_capital / 500).toFixed(2)}x
                          </Typography>
                        </Box>
                      </>
                    )}
                  </Box>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="h6" sx={{ mb: 2 }}>Controls</Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={<PlayArrowIcon />}
                      onClick={() => setDeployDialog(true)}
                      disabled={status.deployment_status === 'DEPLOYED'}
                    >
                      Deploy
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<RefreshIcon />}
                      onClick={fetchDashboard}
                    >
                      Refresh
                    </Button>
                    <Button
                      variant="outlined"
                      startIcon={<GetAppIcon />}
                      href={`${API_BASE}/export/trades`}
                    >
                      Export
                    </Button>
                  </Box>
                </Grid>
              </Grid>
            </Box>
          )}

          {/* Tab 1: Trades */}
          {tabValue === 1 && (
            <Box sx={{ p: 3, overflowX: 'auto' }}>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                      <TableCell>Time</TableCell>
                      {v3Enabled && <TableCell>Strategy</TableCell>}
                      {v3Enabled && <TableCell>Pair</TableCell>}
                      <TableCell align="right">Entry</TableCell>
                      <TableCell align="right">Exit</TableCell>
                      <TableCell align="right">R</TableCell>
                      <TableCell align="right">P&L</TableCell>
                      <TableCell>Outcome</TableCell>
                      <TableCell align="right">{v3Enabled ? 'Balance' : 'Equity'}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(v3Enabled ? v3Data.trades : trades.trades) && (v3Enabled ? v3Data.trades : trades.trades).map((trade, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{new Date(v3Enabled ? trade.exit_time : trade.time).toLocaleString()}</TableCell>
                        {v3Enabled && <TableCell>{trade.strategy}</TableCell>}
                        {v3Enabled && <TableCell>{trade.pair}</TableCell>}
                        <TableCell align="right">{parseFloat(trade.entry_price).toFixed(5)}</TableCell>
                        <TableCell align="right">{parseFloat(trade.exit_price).toFixed(5)}</TableCell>
                        <TableCell align="right">{parseFloat(v3Enabled ? trade.R : trade.r_multiple).toFixed(2)}</TableCell>
                        <TableCell align="right" sx={{ color: parseFloat(v3Enabled ? trade.profit : trade.pnl) >= 0 ? 'green' : 'red' }}>
                          ${parseFloat(v3Enabled ? trade.profit : trade.pnl).toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={trade.outcome}
                            color={trade.outcome === 'WIN' ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">${parseFloat(v3Enabled ? trade.balance : trade.equity).toFixed(2)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}

          {/* Tab 2: Charts */}
          {tabValue === 2 && (
            <Box sx={{ p: 3 }}>
              {chartData.times && chartData.equities && (
                <ResponsiveContainer width="100%" height={400}>
                  <AreaChart data={chartData.times.map((t, i) => ({
                    time: t,
                    equity: chartData.equities[i],
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Area type="monotone" dataKey="equity" stroke="#8884d8" fill="#8884d8" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </Box>
          )}

          {/* Tab 3: V3 Monitor (only if V3 enabled) */}
          {v3Enabled && tabValue === 3 && (
            <Box sx={{ p: 3 }}>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <Alert severity={v3Monitor.trading_enabled ? 'success' : 'error'} sx={{ mb: 2 }}>
                    <Typography variant="h6">
                      {v3Monitor.trading_enabled ? '✅ Trading Active' : '🛑 Trading Halted'}
                    </Typography>
                    {v3Monitor.shutdown_reason && (
                      <Typography variant="body2">
                        Reason: {v3Monitor.shutdown_reason}
                      </Typography>
                    )}
                  </Alert>
                </Grid>

                <Grid item xs={12} md={4}>
                  <StyledPaper>
                    <Typography variant="h6" sx={{ mb: 2 }}>Kill Switch Status</Typography>
                    <Box sx={{ display: 'grid', gap: 2 }}>
                      <Box>
                        <Typography variant="caption" color="textSecondary">Consecutive Loss Days</Typography>
                        <LinearProgress
                          variant="determinate"
                          value={(v3Monitor.consecutive_loss_days || 0) / 3 * 100}
                          sx={{ mt: 1 }}
                          color={(v3Monitor.consecutive_loss_days || 0) >= 3 ? 'error' : 'primary'}
                        />
                        <Typography variant="caption">
                          {v3Monitor.consecutive_loss_days || 0} / 3 days
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="textSecondary">Current Drawdown</Typography>
                        <LinearProgress
                          variant="determinate"
                          value={(v3Monitor.current_drawdown || 0) / 15 * 100}
                          sx={{ mt: 1 }}
                          color={(v3Monitor.current_drawdown || 0) >= 15 ? 'error' : 'primary'}
                        />
                        <Typography variant="caption">
                          {v3Monitor.current_drawdown?.toFixed(1) || 0}% / 15%
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="textSecondary">Sharpe Ratio</Typography>
                        <Typography variant="h6" sx={{ color: (v3Monitor.sharpe_ratio || 0) >= 0.5 ? 'green' : 'red' }}>
                          {v3Monitor.sharpe_ratio?.toFixed(2) || 0}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          Minimum: 0.5
                        </Typography>
                      </Box>
                    </Box>
                  </StyledPaper>
                </Grid>

                <Grid item xs={12} md={8}>
                  <StyledPaper>
                    <Typography variant="h6" sx={{ mb: 2 }}>Recent Alerts</Typography>
                    {v3Monitor.alerts && v3Monitor.alerts.length > 0 ? (
                      <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                        {v3Monitor.alerts.map((alert, idx) => (
                          <Alert 
                            key={idx} 
                            severity={alert.level === 'CRITICAL' ? 'error' : 'warning'}
                            sx={{ mb: 1 }}
                          >
                            <Typography variant="caption" color="textSecondary">
                              {new Date(alert.timestamp).toLocaleString()}
                            </Typography>
                            <Typography variant="body2">{alert.message}</Typography>
                          </Alert>
                        ))}
                      </Box>
                    ) : (
                      <Typography color="textSecondary">No alerts</Typography>
                    )}
                  </StyledPaper>
                </Grid>
              </Grid>
            </Box>
          )}

          {/* Tab 4 (or 3): Settings */}
          {tabValue === (v3Enabled ? 4 : 3) && (
            <Box sx={{ p: 3 }}>
              <Grid container spacing={3}>
                {/* Configuration Info */}
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" sx={{ mb: 2 }}>Deployment Configuration</Typography>
                  <Box sx={{ display: 'grid', gap: 2 }}>
                    <Box>
                      <Typography variant="subtitle2">Strategy</Typography>
                      <Typography color="textSecondary">
                        {v3Enabled ? 'V3 Multi-Strategy Portfolio' : 'V2 Breakout - 7 Component System'}
                      </Typography>
                    </Box>
                    {v3Enabled ? (
                      <>
                        <Box>
                          <Typography variant="subtitle2">Active Strategies</Typography>
                          <Typography color="textSecondary">
                            EUR/USD Breakout, GBP/USD Breakout, USD/JPY Trend
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="subtitle2">Portfolio Risk</Typography>
                          <Typography color="textSecondary">20% max total exposure</Typography>
                        </Box>
                        <Box>
                          <Typography variant="subtitle2">Auto-Optimization</Typography>
                          <Typography color="textSecondary">Every 14 days (walk-forward)</Typography>
                        </Box>
                        <Box>
                          <Typography variant="subtitle2">Capital Management</Typography>
                          <Typography color="textSecondary">50% monthly withdrawal, 50% reinvest</Typography>
                        </Box>
                      </>
                    ) : (
                      <>
                        <Box>
                          <Typography variant="subtitle2">Risk Per Trade</Typography>
                          <Typography color="textSecondary">0.2% (reduced from 0.5%)</Typography>
                        </Box>
                        <Box>
                          <Typography variant="subtitle2">Max Drawdown Limit</Typography>
                          <Typography color="textSecondary">$3,000</Typography>
                        </Box>
                        <Box>
                          <Typography variant="subtitle2">Daily Loss Limit</Typography>
                          <Typography color="textSecondary">$600</Typography>
                        </Box>
                      </>
                    )}
                  </Box>
                </Grid>

                {/* Saxo Credentials */}
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" sx={{ mb: 2 }}>Saxo Bank Credentials</Typography>
                  <Paper sx={{ p: 2, backgroundColor: '#f9f9f9' }}>
                    {credentialMessage && (
                      <Alert severity={credentialMessage.includes('✅') ? 'success' : 'error'} sx={{ mb: 2 }}>
                        {credentialMessage}
                      </Alert>
                    )}
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <TextField
                        label="App ID"
                        value={credentialsForm.app_id}
                        onChange={(e) => setCredentialsForm({...credentialsForm, app_id: e.target.value})}
                        fullWidth
                        size="small"
                        placeholder="Your Saxo App ID"
                      />
                      <TextField
                        label="Access Token"
                        type="password"
                        value={credentialsForm.access_token}
                        onChange={(e) => setCredentialsForm({...credentialsForm, access_token: e.target.value})}
                        fullWidth
                        size="small"
                        placeholder="Your Saxo Bearer Token"
                      />
                      <TextField
                        label="Account ID"
                        value={credentialsForm.account_id}
                        onChange={(e) => setCredentialsForm({...credentialsForm, account_id: e.target.value})}
                        fullWidth
                        size="small"
                        placeholder="Your Saxo Account ID"
                      />
                      <Button 
                        variant="contained" 
                        color="success"
                        onClick={handleSaveCredentials}
                        disabled={savingCredentials}
                        fullWidth
                      >
                        {savingCredentials ? <CircularProgress size={24} /> : 'Save Credentials'}
                      </Button>
                      <Typography variant="caption" color="textSecondary">
                        ℹ️ Credentials are stored securely in the container and used only for authentication.
                      </Typography>
                    </Box>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
          )}
        </StyledPaper>

        {/* Deploy Dialog */}
        <Dialog open={deployDialog} onClose={() => setDeployDialog(false)}>
          <DialogTitle>Start Deployment</DialogTitle>
          <DialogContent>
            <Typography sx={{ my: 2 }}>
              Start demo deployment on Saxo account? This will run for 48-72 hours to validate the strategy.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeployDialog(false)}>Cancel</Button>
            <Button onClick={handleDeploy} variant="contained" disabled={deploying}>
              {deploying ? <CircularProgress size={24} /> : 'Deploy'}
            </Button>
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  );
};

export default Dashboard;
