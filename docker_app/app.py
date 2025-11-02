"""
Trading AI V2 - Web Dashboard Backend
Professional Flask API for monitoring and controlling V2 strategy deployment
"""

from flask import Flask, jsonify, request, send_file, send_from_directory, render_template, make_response
from flask_cors import CORS
from flask_apscheduler import APScheduler
import pandas as pd
import json
import os
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import io
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration - Use local path when running outside Docker
if os.path.exists('/app/data/results'):
    RESULTS_DIR = '/app/data/results'
    BACKTESTS_DIR = '/app/data/backtests'
else:
    # Local development paths
    RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
    BACKTESTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'backtests')

STATUS_FILE = os.path.join(RESULTS_DIR, 'deployment_status.json')
LOG_FILE = os.path.join(RESULTS_DIR, 'live_trades_log_v2.csv')
STATE_FILE = os.path.join(RESULTS_DIR, 'trader_state_v2.json')
CONFIG_FILE = os.path.join(RESULTS_DIR, 'saxo_config.json')

# V3 Multi-Strategy Files
V3_LOG_FILE = os.path.join(RESULTS_DIR, 'live_trades_v3_multi.csv')
V3_STATE_FILE = os.path.join(RESULTS_DIR, 'v3_trader_state.json')
V3_MONITOR_FILE = os.path.join(RESULTS_DIR, 'v3_monitor_state.json')
V3_CAPITAL_FILE = os.path.join(RESULTS_DIR, 'v3_capital_state.json')
V3_SIGNALS_FILE = os.path.join(RESULTS_DIR, 'v3_live_signals.json')

# Ensure directories exist
os.makedirs(RESULTS_DIR, exist_ok=True)

# Initialize APScheduler for background tasks
scheduler = APScheduler()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_status():
    """Get current deployment status"""
    if not os.path.exists(STATUS_FILE):
        return {
            'deployment_status': 'NOT_DEPLOYED',
            'phase': 'IDLE',
            'deployment_time': None,
            'expected_completion': None,
            'tasks_completed': {},
        }
    
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'error': 'Failed to read status file'}

def get_trades_data():
    """Get live trades data with metrics"""
    if not os.path.exists(LOG_FILE):
        return {
            'trades': [],
            'metrics': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'current_equity': 10000.0,
                'max_equity': 10000.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'current_profit': 0.0,
            },
            'last_updated': None,
        }
    
    try:
        df = pd.read_csv(LOG_FILE)
        
        if len(df) == 0:
            return {
                'trades': [],
                'metrics': {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'current_equity': 10000.0,
                    'max_equity': 10000.0,
                    'max_drawdown': 0.0,
                    'profit_factor': 0.0,
                    'current_profit': 0.0,
                },
                'last_updated': None,
            }
        
        # Convert to list of dicts
        trades = df.to_dict('records')
        
        # Calculate metrics
        current_equity = df['equity'].iloc[-1] if 'equity' in df.columns else 10000.0
        max_equity = df['equity'].max() if 'equity' in df.columns else 10000.0
        max_drawdown = max_equity - current_equity
        
        wins = (df['outcome'] == 'WIN').sum() if 'outcome' in df.columns else 0
        losses = (df['outcome'] == 'LOSS').sum() if 'outcome' in df.columns else 0
        win_rate = 100 * wins / len(df) if len(df) > 0 else 0
        
        pf = df['profit_factor'].iloc[-1] if 'profit_factor' in df.columns else 0.0
        
        return {
            'trades': trades[-50:],  # Last 50 trades
            'metrics': {
                'total_trades': len(df),
                'wins': int(wins),
                'losses': int(losses),
                'win_rate': round(win_rate, 2),
                'current_equity': round(current_equity, 2),
                'max_equity': round(max_equity, 2),
                'max_drawdown': round(max_drawdown, 2),
                'profit_factor': round(pf, 3),
                'current_profit': round(current_equity - 10000, 2),
            },
            'last_updated': datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error reading trades data: {e}")
        return {
            'trades': [],
            'metrics': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'current_equity': 10000.0,
                'max_equity': 10000.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'current_profit': 0.0,
            },
            'error': str(e),
        }

def get_trader_state():
    """Get current trader state"""
    if not os.path.exists(STATE_FILE):
        return {'status': 'NO_STATE_FILE'}
    
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'status': 'ERROR_READING_STATE'}

def get_equity_chart_data():
    """Get equity curve data for chart"""
    if not os.path.exists(LOG_FILE):
        return {'times': [], 'equities': []}
    
    try:
        df = pd.read_csv(LOG_FILE)
        
        # Handle both possible formats
        time_column = None
        equity_column = None
        
        if 'exit_time' in df.columns:
            time_column = 'exit_time'
        elif 'time' in df.columns:
            time_column = 'time'
        
        if 'balance' in df.columns:
            equity_column = 'balance'
        elif 'equity' in df.columns:
            equity_column = 'equity'
        
        if time_column and equity_column and len(df) > 0:
            # Convert timestamps and equity to lists
            times = pd.to_datetime(df[time_column]).dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
            equities = pd.to_numeric(df[equity_column], errors='coerce').tolist()
            return {
                'times': times,
                'equities': equities,
            }
        return {'times': [], 'equities': []}
    except Exception as e:
        logger.error(f"Error getting equity chart data: {e}")
        return {'times': [], 'equities': []}

def get_alerts():
    """Get current alerts based on trading metrics"""
    data = get_trades_data()
    metrics = data['metrics']
    alerts = []
    
    # Check for critical conditions
    if metrics['max_drawdown'] > 3000:
        alerts.append({
            'level': 'CRITICAL',
            'message': f"MAX DRAWDOWN EXCEEDED: ${metrics['max_drawdown']:,.0f} (limit: $3,000)",
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    if metrics['current_equity'] < 9400:
        alerts.append({
            'level': 'CRITICAL',
            'message': f"DAILY LOSS FREEZE: Equity ${metrics['current_equity']:,.0f} (limit: $9,400)",
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    if metrics['current_equity'] < 8500:
        alerts.append({
            'level': 'WARNING',
            'message': f"SOFT STOP ACTIVE: Equity ${metrics['current_equity']:,.0f} (limit: $8,500)",
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    if metrics['win_rate'] < 10 and metrics['total_trades'] > 10:
        alerts.append({
            'level': 'WARNING',
            'message': f"WIN RATE LOW: {metrics['win_rate']:.1f}% (target: 12-15%)",
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    if metrics['profit_factor'] < 1.5 and metrics['total_trades'] > 10:
        alerts.append({
            'level': 'WARNING',
            'message': f"PROFIT FACTOR LOW: {metrics['profit_factor']:.2f} (target: 1.8-2.2)",
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    return alerts

def get_config():
    """Get Saxo configuration"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_config(config):
    """Save Saxo configuration"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def get_v3_data():
    """Get V3 multi-strategy trading data"""
    if not os.path.exists(V3_LOG_FILE):
        return {
            'enabled': False,
            'trades': [],
            'strategies': {},
            'portfolio_metrics': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'current_capital': 500.0,
                'total_withdrawn': 0.0,
                'total_value': 500.0,
                'roi': 0.0,
            },
        }
    
    try:
        df = pd.read_csv(V3_LOG_FILE)
        
        if len(df) == 0:
            return {
                'enabled': True,
                'trades': [],
                'strategies': {},
                'portfolio_metrics': {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'current_capital': 500.0,
                    'total_withdrawn': 0.0,
                    'total_value': 500.0,
                    'roi': 0.0,
                },
            }
        
        # Recent trades
        trades = df.tail(50).to_dict('records')
        
        # Strategy breakdown
        strategies = {}
        for strategy_name in df['strategy'].unique():
            strategy_trades = df[df['strategy'] == strategy_name]
            wins = (strategy_trades['outcome'] == 'WIN').sum()
            losses = (strategy_trades['outcome'] == 'LOSS').sum()
            total = len(strategy_trades)
            
            strategies[strategy_name] = {
                'trades': total,
                'wins': int(wins),
                'losses': int(losses),
                'win_rate': round(100 * wins / total, 2) if total > 0 else 0,
                'profit': round(strategy_trades['profit'].sum(), 2),
            }
        
        # Portfolio metrics
        wins = (df['outcome'] == 'WIN').sum()
        losses = (df['outcome'] == 'LOSS').sum()
        
        # Load capital scaler state if exists
        capital_data = {}
        if os.path.exists(V3_CAPITAL_FILE):
            try:
                with open(V3_CAPITAL_FILE, 'r') as f:
                    capital_data = json.load(f)
            except:
                pass
        
        current_capital = capital_data.get('current_capital', df['balance'].iloc[-1] if 'balance' in df.columns else 500.0)
        total_withdrawn = capital_data.get('total_withdrawn', 0.0)
        initial_capital = capital_data.get('initial_capital', 500.0)
        
        total_value = current_capital + total_withdrawn
        roi = 100 * (total_value - initial_capital) / initial_capital if initial_capital > 0 else 0
        
        return {
            'enabled': True,
            'trades': trades,
            'strategies': strategies,
            'portfolio_metrics': {
                'total_trades': len(df),
                'wins': int(wins),
                'losses': int(losses),
                'win_rate': round(100 * wins / len(df), 2) if len(df) > 0 else 0,
                'current_capital': round(current_capital, 2),
                'total_withdrawn': round(total_withdrawn, 2),
                'total_value': round(total_value, 2),
                'roi': round(roi, 2),
                'sharpe_ratio': capital_data.get('latest_sharpe', 0.0),
            },
            'last_updated': datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error reading V3 data: {e}")
        return {
            'enabled': False,
            'error': str(e),
            'trades': [],
            'strategies': {},
            'portfolio_metrics': {},
        }

def get_v3_monitor_status():
    """Get V3 monitoring system status"""
    if not os.path.exists(V3_MONITOR_FILE):
        return {
            'enabled': False,
            'trading_enabled': True,
            'alerts': [],
        }
    
    try:
        with open(V3_MONITOR_FILE, 'r') as f:
            data = json.load(f)
        return {
            'enabled': True,
            'trading_enabled': data.get('trading_enabled', True),
            'shutdown_reason': data.get('shutdown_reason'),
            'total_trades': data.get('total_trades', 0),
            'win_rate': data.get('win_rate', 0.0),
            'sharpe_ratio': data.get('sharpe_ratio', 0.0),
            'consecutive_loss_days': data.get('consecutive_loss_days', 0),
            'current_drawdown': data.get('current_drawdown', 0.0),
            'alerts': data.get('recent_alerts', [])[-10:],  # Last 10 alerts
        }
    except Exception as e:
        logger.error(f"Error reading V3 monitor: {e}")
        return {
            'enabled': False,
            'error': str(e),
        }

def get_v3_live_signals():
    """Get current live trading signals with quality ratings"""
    if not os.path.exists(V3_SIGNALS_FILE):
        return {
            'signals': [],
            'last_check': None,
            'next_check': None,
        }
    
    try:
        with open(V3_SIGNALS_FILE, 'r') as f:
            data = json.load(f)
        
        # Calculate signal quality for each signal
        signals_with_quality = []
        for signal in data.get('signals', []):
            # Calculate quality score based on multiple factors
            quality_score = 0
            quality_factors = []
            
            # Factor 1: Regime (40 points)
            regime = signal.get('regime', 'UNKNOWN')
            if regime == 'TRENDING':
                quality_score += 40
                quality_factors.append('✓ Strong trend detected')
            elif regime == 'RANGING':
                quality_score += 10
                quality_factors.append('⚠ Ranging market')
            else:
                quality_factors.append('❌ Choppy conditions')
            
            # Factor 2: Risk/Reward Ratio (30 points)
            risk_reward = signal.get('risk_reward_ratio', 0)
            if risk_reward >= 3.0:
                quality_score += 30
                quality_factors.append(f'✓ Excellent R:R ({risk_reward:.1f}:1)')
            elif risk_reward >= 2.0:
                quality_score += 20
                quality_factors.append(f'✓ Good R:R ({risk_reward:.1f}:1)')
            else:
                quality_score += 10
                quality_factors.append(f'⚠ Low R:R ({risk_reward:.1f}:1)')
            
            # Factor 3: Portfolio Sharpe Ratio (20 points)
            sharpe = signal.get('portfolio_sharpe', 0)
            if sharpe >= 2.0:
                quality_score += 20
                quality_factors.append(f'✓ High Sharpe ({sharpe:.2f})')
            elif sharpe >= 1.0:
                quality_score += 10
                quality_factors.append(f'✓ Moderate Sharpe ({sharpe:.2f})')
            else:
                quality_factors.append(f'⚠ Low Sharpe ({sharpe:.2f})')
            
            # Factor 4: Win Rate History (10 points)
            win_rate = signal.get('strategy_win_rate', 0)
            if win_rate >= 70:
                quality_score += 10
                quality_factors.append(f'✓ Win rate {win_rate:.0f}%')
            elif win_rate >= 50:
                quality_score += 5
                quality_factors.append(f'✓ Win rate {win_rate:.0f}%')
            
            # Determine quality level
            if quality_score >= 80:
                quality_level = 'HIGH'
                quality_color = '#38ef7d'
                quality_badge = '🔥 HIGH POTENTIAL'
            elif quality_score >= 60:
                quality_level = 'MEDIUM'
                quality_color = '#f5af19'
                quality_badge = '⚡ MEDIUM POTENTIAL'
            else:
                quality_level = 'LOW'
                quality_color = '#ff6b6b'
                quality_badge = '⚠️ LOW POTENTIAL'
            
            signal_enhanced = {
                **signal,
                'quality_score': quality_score,
                'quality_level': quality_level,
                'quality_color': quality_color,
                'quality_badge': quality_badge,
                'quality_factors': quality_factors,
            }
            
            signals_with_quality.append(signal_enhanced)
        
        # Sort by quality score (highest first)
        signals_with_quality.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        return {
            'signals': signals_with_quality,
            'last_check': data.get('last_check'),
            'next_check': data.get('next_check'),
            'total_signals': len(signals_with_quality),
        }
    except Exception as e:
        logger.error(f"Error reading V3 signals: {e}")
        return {
            'signals': [],
            'error': str(e),
        }


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'OK', 'timestamp': datetime.now(timezone.utc).isoformat()})

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get deployment status"""
    return jsonify(get_status())

@app.route('/api/trades', methods=['GET'])
def api_trades():
    """Get live trades data and metrics"""
    return jsonify(get_trades_data())

@app.route('/api/trader-state', methods=['GET'])
def api_trader_state():
    """Get trader state"""
    return jsonify(get_trader_state())

@app.route('/api/chart-data', methods=['GET'])
def api_chart_data():
    """Get equity chart data"""
    return jsonify(get_equity_chart_data())

@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    """Get current alerts"""
    return jsonify({'alerts': get_alerts()})

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    """Get complete dashboard data (one call)"""
    return jsonify({
        'status': get_status(),
        'trades': get_trades_data(),
        'trader_state': get_trader_state(),
        'chart_data': get_equity_chart_data(),
        'alerts': get_alerts(),
        'v3_data': get_v3_data(),
        'v3_monitor': get_v3_monitor_status(),
        'v3_signals': get_v3_live_signals(),
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })

@app.route('/api/v3', methods=['GET'])
def api_v3():
    """Get V3 multi-strategy data"""
    return jsonify(get_v3_data())

@app.route('/api/v3/monitor', methods=['GET'])
def api_v3_monitor():
    """Get V3 monitoring status"""
    return jsonify(get_v3_monitor_status())

@app.route('/api/v3/signals', methods=['GET'])
def api_v3_signals():
    """Get V3 live trading signals with quality ratings"""
    # Debug: log the file path being checked
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"V3_SIGNALS_FILE path: {V3_SIGNALS_FILE}")
    logger.info(f"File exists: {os.path.exists(V3_SIGNALS_FILE)}")
    logger.info(f"RESULTS_DIR: {RESULTS_DIR}")
    return jsonify(get_v3_live_signals())

@app.route('/api/deploy', methods=['POST'])
def api_deploy():
    """Start live trader deployment"""
    try:
        status = get_status()
        
        # Check if already deployed
        if status.get('deployment_status') == 'DEPLOYED':
            return jsonify({'error': 'Already deployed'}), 400
        
        # Update status to DEPLOYED
        status_update = {
            'deployment_status': 'DEPLOYED',
            'phase': 'MONITORING',
            'deployment_time': datetime.now(timezone.utc).isoformat(),
            'expected_completion': (datetime.now(timezone.utc) + timedelta(hours=72)).isoformat(),
            'tasks_completed': {'trader_started': True},
        }
        
        with open(STATUS_FILE, 'w') as f:
            json.dump(status_update, f)
        
        logger.info("Deployment status updated to DEPLOYED")
        
        # Start live trader in background thread
        def run_live_trader():
            try:
                logger.info("Starting live trader...")
                
                # Create initial log file so API knows we're tracking
                log_path = '/app/data/results/live_trades_log_v2.csv'
                if not os.path.exists(log_path):
                    with open(log_path, 'w') as f:
                        f.write('entry_time,exit_time,side,entry_price,exit_price,profit,profit_pct,exit_reason,R,size_mult,balance,outcome\n')
                    logger.info(f"✓ Created initial log file at {log_path}")
                
                # Run demo trader with output logging
                logger.info("Executing: python /app/data/backtests/live_trader_saxo_v2_demo.py")
                cmd = 'cd /app/data && python -u ./backtests/live_trader_saxo_v2_demo.py --interval 60'
                
                # Run WITHOUT capture to let it log to Docker stdout/stderr
                result = subprocess.run(cmd, shell=True, cwd='/app/data')
                logger.info(f"Trader process completed with return code: {result.returncode}")
                
            except subprocess.TimeoutExpired:
                logger.warning("Trader timeout (expected for long-running process)")
            except Exception as e:
                logger.error(f"❌ Error running trader: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Update status on error
                error_status = {
                    'deployment_status': 'ERROR',
                    'phase': 'FAILED',
                    'error': str(e),
                    'error_time': datetime.now(timezone.utc).isoformat(),
                }
                try:
                    with open(STATUS_FILE, 'w') as f:
                        json.dump(error_status, f)
                except:
                    pass
        
        # Launch in daemon thread so it runs independently
        trader_thread = threading.Thread(target=run_live_trader, daemon=True)
        trader_thread.start()
        
        logger.info("Live trader thread started")
        
        return jsonify({
            'status': 'DEPLOYED',
            'message': 'Live trader deployment initiated',
            'deployment_time': status_update['deployment_time'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 200
        
    except Exception as e:
        logger.error(f"Deploy error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def api_validate():
    """Run validation only"""
    try:
        cmd = 'py deploy_complete.py --validate'
        thread = threading.Thread(
            target=lambda: subprocess.run(cmd, shell=True, cwd='/app/data')
        )
        thread.start()
        
        return jsonify({
            'status': 'VALIDATION_INITIATED',
            'message': 'Strategy validation started',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop live trader deployment"""
    try:
        status = get_status()
        
        # Update status to stopped
        status['deployment_status'] = 'STOPPED'
        status['phase'] = 'IDLE'
        status['stop_time'] = datetime.now(timezone.utc).isoformat()
        
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
        
        # Try to kill trader processes
        try:
            subprocess.run(['pkill', '-f', 'live_trader_saxo'], capture_output=True)
        except:
            pass
        
        logger.info("Deployment stopped")
        
        return jsonify({
            'status': 'STOPPED',
            'message': 'Trader has been stopped',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }), 200
        
    except Exception as e:
        logger.error(f"Stop error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/configure', methods=['GET', 'POST'])
def api_configure():
    """Get or set Saxo configuration"""
    if request.method == 'GET':
        # Return configuration (without sensitive data)
        config = get_config()
        return jsonify({
            'configured': bool(config.get('app_id')),
            'app_id': config.get('app_id', ''),
            'has_token': bool(config.get('access_token')),
            'account_id': config.get('account_id', ''),
        })
    
    elif request.method == 'POST':
        # Save configuration
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            config = {
                'app_id': data.get('app_id', ''),
                'access_token': data.get('access_token', ''),
                'account_id': data.get('account_id', ''),
            }
            
            if not all([config['app_id'], config['access_token'], config['account_id']]):
                return jsonify({'error': 'Missing required fields: app_id, access_token, account_id'}), 400
            
            if save_config(config):
                logger.info("Configuration saved successfully")
                return jsonify({
                    'status': 'SUCCESS',
                    'message': 'Configuration saved',
                    'configured': True,
                }), 200
            else:
                return jsonify({'error': 'Failed to save configuration'}), 500
        except Exception as e:
            logger.error(f"Configure error: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Analyze demo results"""
    try:
        data = get_trades_data()
        metrics = data['metrics']
        
        # Generate analysis report
        report = {
            'analysis_time': datetime.now(timezone.utc).isoformat(),
            'metrics': metrics,
            'validation': {
                'win_rate_ok': 10 <= metrics['win_rate'] <= 20,
                'pf_ok': 1.5 <= metrics['profit_factor'] <= 2.5,
                'dd_ok': metrics['max_drawdown'] <= 3000,
            },
            'recommendation': 'PROCEED_TO_LIVE' if all([
                10 <= metrics['win_rate'] <= 20,
                1.5 <= metrics['profit_factor'] <= 2.5,
                metrics['max_drawdown'] <= 3000,
            ]) else 'CONTINUE_DEMO_OR_ITERATE',
        }
        
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/trades', methods=['GET'])
def api_export_trades():
    """Export trades to CSV"""
    try:
        if not os.path.exists(LOG_FILE):
            return jsonify({'error': 'No trades data available'}), 404
        
        with open(LOG_FILE, 'rb') as f:
            return send_file(
                io.BytesIO(f.read()),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
def api_summary():
    """Get strategy summary"""
    return jsonify({
        'strategy': 'V2 Breakout with 7 Risk Components',
        'pair': 'EUR/USD',
        'timeframe': 'Hourly',
        'components': [
            '200-bar MA trend filter',
            'Dynamic position sizing (1.0x -> 0.8x -> 0.5x)',
            'Recovery mode (5 trades at 0.5x)',
            'Equity soft stop (15% below peak)',
            'Reduced risk per trade (0.2%)',
            'Tighter breakout (25 bars)',
            'Tighter ATR stops (0.3x)',
        ],
        'risk_limits': {
            'max_drawdown': 3000,
            'daily_loss': 600,
            'soft_stop_equity': 8500,
        },
        'backtest_results': {
            'win_rate': '70%+',
            'profit_factor': 1.82,
            'max_drawdown': 2500,
        },
    })

# =============================================================================
# BACKGROUND TASKS
# =============================================================================

@scheduler.task('interval', id='refresh_status', seconds=60)
def refresh_status():
    """Periodically refresh status (called by scheduler)"""
    logger.info("Status refresh triggered")

# =============================================================================
# STATIC FILE SERVING (React frontend)
# =============================================================================

@app.route('/')
def serve_v3_live():
    """Serve V3 live dashboard (main page)"""
    return send_from_directory('public', 'index.html')

@app.route('/v3_dashboard.html')
def redirect_old_dashboard():
    """Redirect old V3 dashboard to new multi-page dashboard"""
    from flask import redirect
    return redirect('/', code=302)

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from public directory"""
    return send_from_directory('public', path)

# =============================================================================
# BACKGROUND TASKS
# =============================================================================

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# =============================================================================
# INITIALIZATION
# =============================================================================

if __name__ == '__main__':
    scheduler.init_app(app)
    scheduler.start()
    app.run(host='0.0.0.0', port=5000, debug=False)
