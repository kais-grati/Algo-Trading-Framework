from core.position_manager import BasePositionManager
from data.base_candle import BaseCandle
from data.data_provider import BaseDataProvider, BaseSubscriber
from dataclasses import dataclass, field, asdict
from colorama import Fore, Style

@dataclass
class BaseBacktestStats:
    positions: int = 0  # total number of closed positions (count)
    position_frquency: float = 0.0  # how often positions were opened (positions / exposure_time, per hour)
    longs: int = 0  # number of long positions taken (count)
    shorts: int = 0  # number of short positions taken (count)

    exit_wins: int = 0  # number of exits that hit take profit (count)
    exit_losses: int = 0  # number of exits that hit stop loss (count)
    exit_winrate: float = 0.0  # ratio of exit_wins / (exit_wins + exit_losses) (0.0–1.0)

    position_wins: int = 0  # number of profitable positions closed (count)
    position_losses: int = 0  # number of losing positions closed (count)
    position_winrate: float = 0.0  # ratio of winning positions to total (0.0–1.0)

    long_wins: int = 0  # number of profitable long positions (count)
    long_winrate: float = 0.0  # winrate of long positions (0.0–1.0)
    short_wins: int = 0  # number of profitable short positions (count)
    short_winrate: float = 0.0  # winrate of short positions (0.0–1.0)

    pnl: float = 0.0  # current unrealized profit/loss ($)
    total_pnl: float = 0.0  # cumulative realized profit/loss across all positions ($)
    avg_position_pnl: float = 0.0  # average PnL per position ($)

    gross_profit: float = 0.0  # sum of all profits from winning trades only ($)
    gross_loss: float = 0.0  # sum of all losses from losing trades only ($, negative)
    profit_factor: float = 0.0  # ratio of gross_profit / abs(gross_loss)

    avg_win: float = 0.0  # average profit per winning trade ($)
    avg_loss: float = 0.0  # average loss per losing trade ($)
    max_drawdown: float = 0.0  # maximum equity peak-to-trough drop observed ($)
    max_win: float = 0.0  # largest single-trade profit ($)
    max_loss: float = 0.0  # largest single-trade loss ($)

    equity_curve: list = field(default_factory=list)  # time series of equity values ($)
    max_win_streak: int = 0  # longest streak of consecutive winning positions (count)
    max_loss_streak: int = 0  # longest streak of consecutive losing positions (count)

    exposure_time: float = 0.0  # total time spent with an open position (hours)
    avg_position_duration: float = 0.0  # average position holding time (hours)

    fees_paid: float = 0.0  # total trading fees paid ($)
    position_history: list = field(default_factory=list)  # record of executed trades/events (list of dicts)

    def __str__(self) -> str:
        """Pretty print backtest statistics with color coding and categorization."""
        
        # ANSI color codes
        class Colors:
            HEADER = '\033[95m'
            BLUE = '\033[94m'
            CYAN = '\033[96m'
            GREEN = '\033[92m'
            YELLOW = '\033[93m'
            RED = '\033[91m'
            BOLD = '\033[1m'
            UNDERLINE = '\033[4m'
            END = '\033[0m'
        
        def format_number(value, is_percentage=False, is_currency=False):
            """Format numbers with appropriate styling."""
            if is_percentage:
                return f"{value * 100:.2f}%"
            elif is_currency:
                color = Colors.GREEN if value >= 0 else Colors.RED
                return f"{color}${value:,.2f}{Colors.END}"
            elif isinstance(value, float):
                return f"{value:,.2f}"
            else:
                return f"{value:,}"
        
        def format_metric(label, value, is_percentage=False, is_currency=False, color=Colors.CYAN):
            """Format a metric line with consistent spacing."""
            formatted_value = format_number(value, is_percentage, is_currency)
            return f"  {color}{label:<25}{Colors.END} {formatted_value}"
        
        lines = []
        
        # Header
        lines.append(f"\n{Colors.BOLD}{Colors.UNDERLINE}BACKTEST STATISTICS{Colors.END}")
        lines.append("=" * 50)
        
        # Position Overview
        lines.append(f"\n{Colors.HEADER}{Colors.BOLD}📊 POSITION OVERVIEW{Colors.END}")
        lines.append(format_metric("Total Positions", self.positions))
        lines.append(format_metric("Positions per hour", self.position_frquency, is_currency=False))
        lines.append(format_metric("Long Positions", self.longs))
        lines.append(format_metric("Short Positions", self.shorts))
        lines.append(format_metric("Exposure Time (hours)", self.exposure_time))
        lines.append(format_metric("Avg Position Duration", self.avg_position_duration))
        
        # Win/Loss Analysis
        lines.append(f"\n{Colors.HEADER}{Colors.BOLD}🎯 WIN/LOSS ANALYSIS{Colors.END}")
        lines.append(format_metric("Position Wins", self.position_wins))
        lines.append(format_metric("Position Losses", self.position_losses))
        
        # Color code win rates
        winrate_color = Colors.GREEN if self.position_winrate >= 0.5 else Colors.YELLOW if self.position_winrate >= 0.3 else Colors.RED
        lines.append(f"  {winrate_color}Position Win Rate{Colors.END}      {format_number(self.position_winrate, is_percentage=True)}")
        
        lines.append(format_metric("Exit Wins (TP)", self.exit_wins))
        lines.append(format_metric("Exit Losses (SL)", self.exit_losses))
        
        exit_winrate_color = Colors.GREEN if self.exit_winrate >= 0.5 else Colors.YELLOW if self.exit_winrate >= 0.3 else Colors.RED
        lines.append(f"  {exit_winrate_color}Exit Win Rate{Colors.END}        {format_number(self.exit_winrate, is_percentage=True)}")
        
        # Long/Short Performance
        lines.append(f"\n{Colors.HEADER}{Colors.BOLD}📈 LONG/SHORT PERFORMANCE{Colors.END}")
        lines.append(format_metric("Long Wins", self.long_wins))
        
        long_winrate_color = Colors.GREEN if self.long_winrate >= 0.5 else Colors.YELLOW if self.long_winrate >= 0.3 else Colors.RED
        lines.append(f"  {long_winrate_color}Long Win Rate{Colors.END}        {format_number(self.long_winrate, is_percentage=True)}")
        
        lines.append(format_metric("Short Wins", self.short_wins))
        
        short_winrate_color = Colors.GREEN if self.short_winrate >= 0.5 else Colors.YELLOW if self.short_winrate >= 0.3 else Colors.RED
        lines.append(f"  {short_winrate_color}Short Win Rate{Colors.END}       {format_number(self.short_winrate, is_percentage=True)}")
        
        # Profit & Loss
        lines.append(f"\n{Colors.HEADER}{Colors.BOLD}💰 PROFIT & LOSS{Colors.END}")
        lines.append(format_metric("Current PnL", self.pnl, is_currency=True))
        lines.append(format_metric("Total PnL", self.total_pnl, is_currency=True))
        lines.append(format_metric("Avg Position PnL", self.avg_position_pnl, is_currency=True))
        lines.append(format_metric("Gross Profit", self.gross_profit, is_currency=True))
        lines.append(format_metric("Gross Loss", self.gross_loss, is_currency=True))
        
        # Profit Factor with color coding
        pf_color = Colors.GREEN if self.profit_factor >= 1.5 else Colors.YELLOW if self.profit_factor >= 1.0 else Colors.RED
        lines.append(f"  {pf_color}Profit Factor{Colors.END}         {format_number(self.profit_factor)}")
        
        lines.append(format_metric("Average Win", self.avg_win, is_currency=True))
        lines.append(format_metric("Average Loss", self.avg_loss, is_currency=True))
        
        # Risk Metrics
        lines.append(f"\n{Colors.HEADER}{Colors.BOLD}⚠️  RISK METRICS{Colors.END}")
        
        # Max drawdown with color coding
        dd_color = Colors.RED if abs(self.max_drawdown) > 1000 else Colors.YELLOW if abs(self.max_drawdown) > 500 else Colors.GREEN
        lines.append(f"  {dd_color}Max Drawdown{Colors.END}          {format_number(self.max_drawdown, is_currency=True)}")
        
        lines.append(format_metric("Max Single Win", self.max_win, is_currency=True))
        lines.append(format_metric("Max Single Loss", self.max_loss, is_currency=True))
        lines.append(format_metric("Max Win Streak", self.max_win_streak))
        lines.append(format_metric("Max Loss Streak", self.max_loss_streak))
        
        # Trading Costs
        lines.append(f"\n{Colors.HEADER}{Colors.BOLD}💸 TRADING COSTS{Colors.END}")
        lines.append(format_metric("Total Fees Paid", self.fees_paid, is_currency=True))
        
        # Footer
        lines.append(f"\n{'=' * 50}")
        
        return '\n'.join(lines)


class BaseBacktester():
    def __init__(self, position_manager: BasePositionManager):
        self.position_manager = position_manager
        self.stats = BaseBacktestStats()
        self.w_streak = 0
        self.l_streak = 0
        self.peak_equity = 0.0

    def update(self, candle: BaseCandle) -> None:

        pos = self.position_manager.position

        # Handle open position: TP, SL, Liquidation
        if pos: 

            if pos.qty > 0:
                # self.stats.pnl = self.position_manager.get_unrealized_pnl(candle)
                # self.stats.equity_curve.append(self.stats.pnl + self.stats.total_pnl)
                # self.stats.max_drawdown = min(self.stats.max_drawdown, self.stats.pnl + self.stats.total_pnl)

                # Take-Profit
                for idx, (tp_price, tp_qty) in enumerate(pos.tp):
                    if (pos.side == pos.side.LONG and candle.high >= tp_price) or \
                    (pos.side == pos.side.SHORT and candle.low <= tp_price):
                        pos.tp.pop(idx)
                        self.position_manager.set_hit_take_profit()
                        self.position_manager.close(candle, qty=tp_qty)
                        self.stats.exit_wins += 1
                        self.stats.position_history.append({'type': 'tp', 'price': tp_price, 'candle': candle})
        

                # Stop-Loss
                for idx, (sl_price, sl_qty) in enumerate(pos.sl):
                    if (pos.side == pos.side.LONG and candle.low <= sl_price) or \
                    (pos.side == pos.side.SHORT and candle.high >= sl_price):
                        pos.sl.pop(idx)
                        self.position_manager.set_hit_stop_loss()
                        self.position_manager.close(candle, qty=sl_qty)
                        self.stats.exit_losses += 1
                        self.stats.position_history.append({'type': 'sl', 'price': sl_price, 'candle': candle})
                        
                    
            # Check if positon is closed
            if pos.qty == 0:
                # Check if position is a win
                if pos.realized_pnl > 0:
                    self.stats.position_wins += 1
                    self.stats.gross_profit += pos.realized_pnl
                    self.stats.max_win = max(self.stats.max_win, pos.realized_pnl)
                    self.w_streak += 1
                    self.l_streak = 0
                    if pos.side == pos.side.LONG:
                        self.stats.long_wins += 1
                    elif pos.side == pos.side.SHORT:
                        self.stats.short_wins += 1
                else:
                    self.stats.position_losses += 1
                    self.stats.gross_loss += pos.realized_pnl
                    self.stats.max_loss = min(self.stats.max_loss, pos.realized_pnl)
                    self.l_streak += 1
                    self.w_streak = 0

                open_time = pos.entry_orders[0].timestamp
                close_time = pos.exit_orders[-1].timestamp
                duration = (close_time - open_time).total_seconds() / 3600
                self.stats.exposure_time += duration
                self.stats.avg_position_duration = self.stats.exposure_time / self.stats.positions if self.stats.positions > 0 else 0.0

                self.stats.max_win_streak = max(self.stats.max_win_streak, self.w_streak)
                self.stats.max_loss_streak = max(self.stats.max_loss_streak, self.l_streak)
                self.stats.total_pnl += pos.realized_pnl
                self.stats.avg_win = self.stats.gross_profit / self.stats.position_wins if self.stats.exit_wins > 0 else 0.0
                self.stats.avg_loss = self.stats.gross_loss / self.stats.position_losses if self.stats.exit_losses > 0 else 0.0


        self.stats.positions = self.position_manager.position_count
        self.stats.fees_paid = self.position_manager.total_fees
        total_exits = self.stats.exit_wins + self.stats.exit_losses
        self.stats.exit_winrate = (self.stats.exit_wins / total_exits) if total_exits > 0 else 0.0
        self.stats.profit_factor = (self.stats.gross_profit / abs(self.stats.gross_loss)) if self.stats.gross_loss < 0 else float('nan')
        self.stats.longs = self.position_manager.total_longs
        self.stats.long_winrate = (self.stats.long_wins / self.stats.longs) if self.stats.longs > 0 else 0.0
        self.stats.shorts = self.position_manager.total_shorts
        self.stats.short_winrate = (self.stats.short_wins / self.stats.shorts) if self.stats.shorts > 0 else 0.0
        self.stats.position_winrate = (self.stats.position_wins / self.stats.positions) if self.stats.positions > 0 else 0.0
        self.stats.position_frquency = self.stats.positions / self.stats.exposure_time if self.stats.exposure_time > 0 else 0.0
        self.stats.avg_position_pnl = self.stats.total_pnl / self.stats.positions if self.stats.positions > 0 else 0.0

        equity = self.stats.pnl + self.stats.total_pnl
        self.stats.equity_curve.append(equity)

        # Track peak equity
        self.peak_equity = max(self.peak_equity, equity)

        # Drawdown = peak - current equity
        drawdown = self.peak_equity - equity
        self.stats.max_drawdown = max(self.stats.max_drawdown, drawdown)



# TODO: Handle liquidation, margin and leverage logic
            # Liquidation: price moves 100% against entry
            # if pos.side == pos.side.LONG:
            #     liquidation_price = pos.avg_price * 0  # 100% down = zero
            #     if candle.low <= liquidation_price:
            #         self.position_manager.close(candle)
            #         self.stats.positions += 1
            #         self.stats.liquidations += 1
            #         self.stats.position_history.append({'type': 'liquidation', 'price': liquidation_price, 'candle': candle})
            #         return
            # elif pos.side == pos.side.SHORT:
            #     liquidation_price = pos.avg_price * 2  # 100% up = double
            #     if candle.high >= liquidation_price:
            #         self.position_manager.close(candle)
            #         self.stats.positions += 1
            #         self.stats.liquidations += 1
            #         self.stats.position_history.append({'type': 'liquidation', 'price': liquidation_price, 'candle': candle})
            #         return

        # Let the strategy act (open/close positions)

    def get_results(self) -> dict:
        return asdict(self.stats)
    
        
    def __str__(self) -> str:
        return str(self.stats)
    
