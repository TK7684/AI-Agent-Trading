#!/usr/bin/env python3
"""
TradingView-Inspired AI Trading Dashboard
Modern, professional interface with TradingView color scheme and layout
"""

import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk


class TradingViewDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.start_monitoring()

    def setup_window(self):
        """Setup main window with TradingView styling."""
        self.root.title("AI Trading System - TradingView Style")
        self.root.geometry("1400x900")
        self.root.configure(bg='#131722')  # TradingView dark background

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"1400x900+{x}+{y}")

    def setup_styles(self):
        """Setup TradingView-inspired styling."""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # TradingView color palette
        self.colors = {
            'bg_dark': '#131722',       # TradingView dark background
            'bg_medium': '#1E222D',     # TradingView medium background
            'bg_light': '#2A2E39',      # TradingView light background
            'accent': '#2962FF',        # TradingView blue accent
            'success': '#4CAF50',       # TradingView green (bullish)
            'warning': '#FF9800',       # TradingView orange (warning)
            'error': '#F44336',         # TradingView red (bearish)
            'text': '#D1D4DC',          # TradingView primary text
            'text_dim': '#787B86',      # TradingView secondary text
            'highlight': '#363A45',     # TradingView hover/highlight
            'border': '#363A45',        # TradingView border color
            'chart_green': '#26A69A',   # TradingView chart green
            'chart_red': '#EF5350'      # TradingView chart red
        }

        # Configure ttk styles
        self.style.configure('TV.TFrame', background=self.colors['bg_medium'])
        self.style.configure('TVDark.TFrame', background=self.colors['bg_dark'])
        self.style.configure('TVLight.TFrame', background=self.colors['bg_light'])

        self.style.configure('TV.TLabel', background=self.colors['bg_medium'],
                           foreground=self.colors['text'], font=('Segoe UI', 10))
        self.style.configure('TVTitle.TLabel', background=self.colors['bg_medium'],
                           foreground=self.colors['text'], font=('Segoe UI', 14, 'bold'))
        self.style.configure('TVDim.TLabel', background=self.colors['bg_medium'],
                           foreground=self.colors['text_dim'], font=('Segoe UI', 9))

        # Notebook (tabs) styling
        self.style.configure('TV.TNotebook', background=self.colors['bg_dark'],
                           borderwidth=0, relief='flat')
        self.style.configure('TV.TNotebook.Tab',
                           background=self.colors['bg_medium'],
                           foreground=self.colors['text_dim'],
                           padding=[20, 12],
                           font=('Segoe UI', 10, 'normal'),
                           borderwidth=0)

        self.style.map('TV.TNotebook.Tab',
                      background=[('selected', self.colors['bg_light']),
                                ('active', self.colors['highlight']),
                                ('!selected', self.colors['bg_medium'])],
                      foreground=[('selected', self.colors['accent']),
                                ('active', self.colors['text']),
                                ('!selected', self.colors['text_dim'])])

    def create_widgets(self):
        """Create main interface widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, style='TVDark.TFrame')
        main_frame.pack(fill='both', expand=True)

        # Top toolbar
        self.create_toolbar(main_frame)

        # Main content area
        content_frame = ttk.Frame(main_frame, style='TVDark.TFrame')
        content_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(content_frame, style='TV.TNotebook')
        self.notebook.pack(fill='both', expand=True)

        # Create tabs
        self.create_dashboard_tab()
        self.create_trading_tab()
        self.create_analysis_tab()
        self.create_settings_tab()

    def create_toolbar(self, parent):
        """Create TradingView-style toolbar."""
        toolbar = tk.Frame(parent, bg=self.colors['bg_medium'], height=50)
        toolbar.pack(fill='x', padx=10, pady=10)
        toolbar.pack_propagate(False)

        # Left side - Title and status
        left_frame = tk.Frame(toolbar, bg=self.colors['bg_medium'])
        left_frame.pack(side='left', fill='y')

        title_label = tk.Label(left_frame, text="AI Trading System",
                              bg=self.colors['bg_medium'], fg=self.colors['text'],
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack(side='left', padx=10, pady=15)

        version_label = tk.Label(left_frame, text="v2.0 Pro",
                                bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                                font=('Segoe UI', 9))
        version_label.pack(side='left', padx=(5, 0), pady=15)

        # Right side - Status indicators
        right_frame = tk.Frame(toolbar, bg=self.colors['bg_medium'])
        right_frame.pack(side='right', fill='y')

        # Market status
        market_frame = tk.Frame(right_frame, bg=self.colors['bg_medium'])
        market_frame.pack(side='right', padx=15, pady=12)

        mk_label = tk.Label(market_frame, text="Market:",
                           bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                           font=('Segoe UI', 9))
        mk_label.pack(side='left')

        self.market_status = tk.Label(market_frame, text="🟢 OPEN",
                                     bg=self.colors['bg_medium'], fg=self.colors['chart_green'],
                                     font=('Segoe UI', 9, 'bold'))
        self.market_status.pack(side='left', padx=(5, 0))

        # System status
        system_frame = tk.Frame(right_frame, bg=self.colors['bg_medium'])
        system_frame.pack(side='right', padx=15, pady=12)

        sys_label = tk.Label(system_frame, text="System:",
                            bg=self.colors['bg_medium'], fg=self.colors['text_dim'],
                            font=('Segoe UI', 9))
        sys_label.pack(side='left')

        self.system_status = tk.Label(system_frame, text="🔵 ACTIVE",
                                     bg=self.colors['bg_medium'], fg=self.colors['accent'],
                                     font=('Segoe UI', 9, 'bold'))
        self.system_status.pack(side='left', padx=(5, 0))

    def create_dashboard_tab(self):
        """Create TradingView-style dashboard tab."""
        dashboard_frame = ttk.Frame(self.notebook, style='TVDark.TFrame')
        self.notebook.add(dashboard_frame, text="📊 Dashboard")

        # Main content
        content = tk.Frame(dashboard_frame, bg=self.colors['bg_dark'])
        content.pack(fill='both', expand=True, padx=15, pady=15)

        # Top metrics row
        metrics_row = tk.Frame(content, bg=self.colors['bg_dark'])
        metrics_row.pack(fill='x', pady=(0, 15))

        # Key performance metrics
        metrics = [
            ("Portfolio Value", "$125,890", "+8.34%", self.colors['chart_green']),
            ("Today's P&L", "+$1,234", "+0.98%", self.colors['chart_green']),
            ("Win Rate", "73.2%", "+1.5%", self.colors['success']),
            ("Active Positions", "5", "2L • 3S", self.colors['accent'])
        ]

        for i, (label, value, change, color) in enumerate(metrics):
            card = self.create_metric_card(metrics_row, label, value, change, color)
            card.pack(side='left', fill='x', expand=True,
                     padx=(0, 10) if i < len(metrics)-1 else (0, 0))

        # Main content area
        main_row = tk.Frame(content, bg=self.colors['bg_dark'])
        main_row.pack(fill='both', expand=True, pady=(0, 15))

        # Left panel - Market overview
        left_panel = self.create_panel(main_row, "📈 Market Overview")
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))

        market_text = tk.Text(left_panel, bg=self.colors['bg_light'], fg=self.colors['text'],
                             font=('Consolas', 9), relief='flat', bd=0, insertbackground=self.colors['accent'])
        market_text.pack(fill='both', expand=True, padx=1, pady=(0, 1))

        market_data = """📊 MAJOR PAIRS • LIVE PRICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EURUSD    1.0875  ▲ +0.0023  (+0.21%)  🟢 BULLISH
GBPUSD    1.2634  ▼ -0.0012  (-0.09%)  🔴 BEARISH
USDJPY    149.85  ▲ +0.45    (+0.30%)  🟢 BULLISH
USDCHF    0.8756  ▼ -0.0008  (-0.09%)  🔴 BEARISH
AUDUSD    0.6543  ▲ +0.0015  (+0.23%)  🟢 BULLISH
NZDUSD    0.5987  ▲ +0.0008  (+0.13%)  🟢 BULLISH

🎯 AI SIGNALS • TODAY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ EURUSD LONG    Entry: 1.0852   Current: +23 pips   🟢
⏳ GBPUSD SHORT   Entry: 1.2648   Status: PENDING     🟡
✅ USDJPY LONG    Entry: 149.12   Current: +73 pips   🟢
🔄 AUDUSD         Status: ANALYZING...               🔵
⚠️  USDCHF        Signal: WEAK (Filtered out)       🟠

📈 MARKET SENTIMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Trend:     BULLISH USD     Strength: 7.5/10
Volatility:        MEDIUM          VIX: 18.4
Risk Sentiment:    RISK ON         Fear/Greed: 65
Session:           LONDON OPEN     Volume: HIGH"""

        market_text.insert(1.0, market_data)
        market_text.config(state='disabled')

        # Right panel - System status
        right_panel = self.create_panel(main_row, "⚡ System Status")
        right_panel.pack(side='right', fill='both', expand=False, padx=(0, 0))
        right_panel.config(width=350)

        status_text = tk.Text(right_panel, bg=self.colors['bg_light'], fg=self.colors['text'],
                             font=('Consolas', 9), relief='flat', bd=0, insertbackground=self.colors['accent'])
        status_text.pack(fill='both', expand=True, padx=1, pady=(0, 1))

        system_data = """🚀 SYSTEM HEALTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 Trading Engine      ONLINE
🟢 Risk Manager        ACTIVE
🟢 Pattern AI          RUNNING
🟢 Market Data         LIVE
🟢 Order Execution     READY
🟢 WebSocket           CONNECTED

⚡ PERFORMANCE METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API Latency:           12ms
Order Execution:       8ms
System Uptime:         99.8%
Memory Usage:          2.1GB
CPU Usage:             15%
Network:               STABLE

🛡️ RISK MANAGEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Drawdown:      -1.2%
Risk Per Trade:        0.5%
Portfolio Heat:        15%
Max Risk Limit:        2.0%
Stop Loss:             ACTIVE
Position Sizing:       AUTO

📊 TODAY'S STATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Signals Generated:     12
Signals Executed:      3
Win Rate:              73.2%
Profit Factor:         2.8
Best Trade:            +$567
Worst Trade:           -$89"""

        status_text.insert(1.0, system_data)
        status_text.config(state='disabled')

    def create_trading_tab(self):
        """Create trading controls tab."""
        trading_frame = ttk.Frame(self.notebook, style='TVDark.TFrame')
        self.notebook.add(trading_frame, text="💹 Trading")

        content = tk.Frame(trading_frame, bg=self.colors['bg_dark'])
        content.pack(fill='both', expand=True, padx=15, pady=15)

        # Quick actions panel
        actions_panel = self.create_panel(content, "🎯 Quick Actions")
        actions_panel.pack(fill='x', pady=(0, 15))

        actions_content = tk.Frame(actions_panel, bg=self.colors['bg_light'])
        actions_content.pack(fill='x', padx=10, pady=10)

        # Action buttons
        buttons = [
            ("🚀 Start Live Trading", self.start_trading, self.colors['success']),
            ("📊 Paper Trading", self.start_paper, self.colors['accent']),
            ("⏹️ Stop All", self.stop_trading, self.colors['error']),
            ("🔄 Refresh Data", self.refresh_data, self.colors['warning'])
        ]

        for i, (text, command, color) in enumerate(buttons):
            btn = tk.Button(actions_content, text=text, command=command,
                           bg=color, fg='white', font=('Segoe UI', 11, 'bold'),
                           relief='flat', padx=20, pady=10, cursor='hand2',
                           activebackground=self.colors['highlight'])
            btn.grid(row=i//2, column=i%2, padx=10, pady=5, sticky='ew')

        actions_content.grid_columnconfigure(0, weight=1)
        actions_content.grid_columnconfigure(1, weight=1)

    def create_analysis_tab(self):
        """Create analysis tab."""
        analysis_frame = ttk.Frame(self.notebook, style='TVDark.TFrame')
        self.notebook.add(analysis_frame, text="🧠 Analysis")

        content = tk.Frame(analysis_frame, bg=self.colors['bg_dark'])
        content.pack(fill='both', expand=True, padx=15, pady=15)

        # AI Analysis panel
        ai_panel = self.create_panel(content, "🤖 AI Market Analysis")
        ai_panel.pack(fill='both', expand=True)

        ai_text = tk.Text(ai_panel, bg=self.colors['bg_light'], fg=self.colors['text'],
                         font=('Segoe UI', 10), relief='flat', bd=0, insertbackground=self.colors['accent'])
        ai_text.pack(fill='both', expand=True, padx=10, pady=10)

        ai_analysis = """🧠 AI MARKET ANALYSIS • REAL-TIME INSIGHTS
════════════════════════════════════════════════════════════════════════

📈 TREND ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Primary Trend: BULLISH USD across major pairs
• Timeframe: H4 and Daily alignment showing strength
• Support/Resistance: Key levels holding, breakout potential high
• Volume Analysis: Above-average participation, confirming moves

🔍 PATTERN RECOGNITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• EURUSD: Double Bottom formation confirmed, target 1.0950
• GBPUSD: Descending Triangle, bearish breakout likely
• USDJPY: Ascending Channel, riding the uptrend
• Gold: Head & Shoulders pattern, potential reversal zone

📊 SENTIMENT INDICATORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• COT Report: Large specs increasing USD long positions
• VIX: 18.4 (Moderate volatility, favorable for trend following)
• Fear & Greed Index: 65 (Greed territory, but not extreme)
• News Sentiment: Positive USD bias from Fed hawkish stance

🎯 TRADE RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. EURUSD LONG: Entry 1.0860-1.0870, Target 1.0950, SL 1.0820
2. USDJPY LONG: Entry 149.50-149.80, Target 151.00, SL 148.80
3. GBPUSD SHORT: Wait for break below 1.2600, Target 1.2450

⚠️  RISK FACTORS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• ECB meeting next week could impact EUR pairs
• US CPI data tomorrow - high impact event
• Geopolitical tensions may cause safe-haven flows
• Month-end flows could create temporary volatility

📋 CONFIDENCE LEVELS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Market Direction: 85% confidence
Individual Trade Setups: 78% average confidence
Risk Assessment: 92% confidence in current risk levels
System Performance: 94% confidence in execution quality"""

        ai_text.insert(1.0, ai_analysis)
        ai_text.config(state='disabled')

    def create_settings_tab(self):
        """Create settings tab."""
        settings_frame = ttk.Frame(self.notebook, style='TVDark.TFrame')
        self.notebook.add(settings_frame, text="⚙️ Settings")

        content = tk.Frame(settings_frame, bg=self.colors['bg_dark'])
        content.pack(fill='both', expand=True, padx=15, pady=15)

        # Settings panels
        risk_panel = self.create_panel(content, "🛡️ Risk Management")
        risk_panel.pack(fill='x', pady=(0, 15))

        # Risk settings
        risk_content = tk.Frame(risk_panel, bg=self.colors['bg_light'])
        risk_content.pack(fill='x', padx=10, pady=10)

        settings = [
            ("Max Position Size %", "2.0"),
            ("Risk Per Trade %", "0.5"),
            ("Max Daily Loss %", "5.0"),
            ("Stop Loss %", "1.0")
        ]

        for i, (label, value) in enumerate(settings):
            tk.Label(risk_content, text=label, bg=self.colors['bg_light'],
                    fg=self.colors['text'], font=('Segoe UI', 10)).grid(row=i, column=0, sticky='w', padx=10, pady=5)

            entry = tk.Entry(risk_content, bg=self.colors['bg_medium'], fg=self.colors['text'],
                           font=('Segoe UI', 10), relief='flat', bd=1)
            entry.insert(0, value)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky='ew')

        risk_content.grid_columnconfigure(1, weight=1)

        # Save button
        save_btn = tk.Button(risk_content, text="💾 Save Settings",
                           bg=self.colors['accent'], fg='white',
                           font=('Segoe UI', 11, 'bold'), relief='flat',
                           padx=20, pady=8, cursor='hand2')
        save_btn.grid(row=len(settings), column=0, columnspan=2, pady=15)

    def create_metric_card(self, parent, label, value, change, color):
        """Create TradingView-style metric card."""
        card = tk.Frame(parent, bg=self.colors['bg_light'], relief='flat', bd=1)

        # Label
        label_widget = tk.Label(card, text=label, bg=self.colors['bg_light'],
                               fg=self.colors['text_dim'], font=('Segoe UI', 9))
        label_widget.pack(anchor='w', padx=15, pady=(15, 2))

        # Value
        value_widget = tk.Label(card, text=value, bg=self.colors['bg_light'],
                               fg=color, font=('Segoe UI', 18, 'bold'))
        value_widget.pack(anchor='w', padx=15, pady=(0, 2))

        # Change
        change_widget = tk.Label(card, text=change, bg=self.colors['bg_light'],
                                fg=self.colors['text_dim'], font=('Segoe UI', 9))
        change_widget.pack(anchor='w', padx=15, pady=(0, 15))

        return card

    def create_panel(self, parent, title):
        """Create TradingView-style panel with title bar."""
        panel = tk.Frame(parent, bg=self.colors['bg_medium'], relief='flat', bd=1)

        # Title bar
        title_bar = tk.Frame(panel, bg=self.colors['bg_medium'], height=35)
        title_bar.pack(fill='x')
        title_bar.pack_propagate(False)

        title_label = tk.Label(title_bar, text=title, bg=self.colors['bg_medium'],
                              fg=self.colors['text'], font=('Segoe UI', 11, 'bold'))
        title_label.pack(side='left', padx=15, pady=10)

        return panel

    def start_monitoring(self):
        """Start background monitoring thread."""
        def monitor():
            while True:
                try:
                    # Update status indicators
                    current_time = datetime.now().strftime("%H:%M:%S")

                    # Simulate market status
                    if 9 <= datetime.now().hour <= 17:
                        self.market_status.config(text="🟢 OPEN", fg=self.colors['chart_green'])
                    else:
                        self.market_status.config(text="🔴 CLOSED", fg=self.colors['chart_red'])

                    time.sleep(5)
                except:
                    break

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

    # Button command methods
    def start_trading(self):
        messagebox.showinfo("Trading", "🚀 Live trading started!")

    def start_paper(self):
        messagebox.showinfo("Paper Trading", "📊 Paper trading mode activated!")

    def stop_trading(self):
        messagebox.showinfo("Stop", "⏹️ All trading stopped!")

    def refresh_data(self):
        messagebox.showinfo("Refresh", "🔄 Market data refreshed!")

    def run(self):
        """Start the application."""
        self.root.mainloop()

if __name__ == "__main__":
    app = TradingViewDashboard()
    app.run()
