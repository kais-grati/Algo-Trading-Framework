from core.position_manager import BasePositionManager
from data.base_candle import BaseCandle
from dataclasses import dataclass, field, asdict
from colorama import Fore, Style
import time
import numpy as np
from pathlib import Path
from collections import deque
import numpy as np


@dataclass(slots=True)
class BaseBacktestStats:
    positions: int = 0
    position_frquency: float = 0.0
    longs: int = 0
    shorts: int = 0

    exit_wins: int = 0
    exit_losses: int = 0
    exit_winrate: float = 0.0

    position_wins: int = 0
    position_losses: int = 0
    position_winrate: float = 0.0

    long_wins: int = 0
    long_winrate: float = 0.0
    short_wins: int = 0
    short_winrate: float = 0.0

    pnl: float = 0.0
    total_pnl: float = 0.0
    avg_position_pnl: float = 0.0

    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0

    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0

    equity: float = 0.0
    peak_equity: float = 0.0
    max_win_streak: int = 0
    max_loss_streak: int = 0

    sharpe_ratio: float = 0.0

    exposure_time: float = 0.0
    avg_position_duration: float = 0.0

    fees_paid: float = 0.0

    current_price: float = 0.0
    current_position_info: dict = field(default_factory=dict)

    def __str__(self) -> str:
        """Optimized pretty print with pre-computed values."""
        
        # Pre-compute all formatted values at once
        positions_str = f"{self.positions:,}"
        freq_str = f"{self.position_frquency:,.2f}"
        longs_str = f"{self.longs:,}"
        shorts_str = f"{self.shorts:,}"
        exposure_str = f"{self.exposure_time:,.2f}"
        avg_dur_str = f"{self.avg_position_duration:,.2f}"
        
        pos_wins_str = f"{self.position_wins:,}"
        pos_losses_str = f"{self.position_losses:,}"
        pos_winrate_pct = self.position_winrate * 100
        exit_wins_str = f"{self.exit_wins:,}"
        exit_losses_str = f"{self.exit_losses:,}"
        exit_winrate_pct = self.exit_winrate * 100
        
        long_wins_str = f"{self.long_wins:,}"
        long_winrate_pct = self.long_winrate * 100
        short_wins_str = f"{self.short_wins:,}"
        short_winrate_pct = self.short_winrate * 100
        
        # Currency formatting with color
        pnl_color = '\033[92m' if self.pnl >= 0 else '\033[91m'
        total_pnl_color = '\033[92m' if self.total_pnl >= 0 else '\033[91m'
        avg_pnl_color = '\033[92m' if self.avg_position_pnl >= 0 else '\033[91m'
        gross_profit_color = '\033[92m' if self.gross_profit >= 0 else '\033[91m'
        gross_loss_color = '\033[92m' if self.gross_loss >= 0 else '\033[91m'
        avg_win_color = '\033[92m' if self.avg_win >= 0 else '\033[91m'
        avg_loss_color = '\033[92m' if self.avg_loss >= 0 else '\033[91m'
        max_win_color = '\033[92m' if self.max_win >= 0 else '\033[91m'
        max_loss_color = '\033[92m' if self.max_loss >= 0 else '\033[91m'
        fees_color = '\033[92m' if self.fees_paid >= 0 else '\033[91m'
        
        # Winrate colors
        pos_wr_color = '\033[92m' if pos_winrate_pct >= 50 else '\033[93m' if pos_winrate_pct >= 30 else '\033[91m'
        exit_wr_color = '\033[92m' if exit_winrate_pct >= 50 else '\033[93m' if exit_winrate_pct >= 30 else '\033[91m'
        long_wr_color = '\033[92m' if long_winrate_pct >= 50 else '\033[93m' if long_winrate_pct >= 30 else '\033[91m'
        short_wr_color = '\033[92m' if short_winrate_pct >= 50 else '\033[93m' if short_winrate_pct >= 30 else '\033[91m'
        pf_color = '\033[92m' if self.profit_factor >= 1.5 else '\033[93m' if self.profit_factor >= 1.0 else '\033[91m'
        
        end = '\033[0m'
        
        # Build string using list join (faster than concatenation)
        return (
            f"\n\033[1m\033[4mBACKTEST STATISTICS{end}\n"
            f"{'=' * 50}\n"
            f"\n\033[95m\033[1m📊 POSITION OVERVIEW{end}\n"
            f"  \033[96mTotal Positions{end}          {positions_str}\n"
            f"  \033[96mPositions per hour{end}       {freq_str}\n"
            f"  \033[96mLong Positions{end}           {longs_str}\n"
            f"  \033[96mShort Positions{end}          {shorts_str}\n"
            f"  \033[96mExposure Time (hours){end}    {exposure_str}\n"
            f"  \033[96mAvg Position Duration{end}    {avg_dur_str}\n"
            f"\n\033[95m\033[1m🎯 WIN/LOSS ANALYSIS{end}\n"
            f"  \033[96mPosition Wins{end}            {pos_wins_str}\n"
            f"  \033[96mPosition Losses{end}          {pos_losses_str}\n"
            f"  {pos_wr_color}Position Win Rate{end}      {pos_winrate_pct:.2f}%\n"
            f"  \033[96mExit Wins (TP){end}           {exit_wins_str}\n"
            f"  \033[96mExit Losses (SL){end}         {exit_losses_str}\n"
            f"  {exit_wr_color}Exit Win Rate{end}        {exit_winrate_pct:.2f}%\n"
            f"\n\033[95m\033[1m📈 LONG/SHORT PERFORMANCE{end}\n"
            f"  \033[96mLong Wins{end}                {long_wins_str}\n"
            f"  {long_wr_color}Long Win Rate{end}        {long_winrate_pct:.2f}%\n"
            f"  \033[96mShort Wins{end}               {short_wins_str}\n"
            f"  {short_wr_color}Short Win Rate{end}       {short_winrate_pct:.2f}%\n"
            f"\n\033[95m\033[1m💰 PROFIT & LOSS{end}\n"
            f"  \033[96mCurrent PnL{end}              {pnl_color}${self.pnl:,.2f}{end}\n"
            f"  \033[96mTotal PnL{end}                {total_pnl_color}${self.total_pnl:,.2f}{end}\n"
            f"  \033[96mAvg Position PnL{end}         {avg_pnl_color}${self.avg_position_pnl:,.2f}{end}\n"
            f"  \033[96mGross Profit{end}             {gross_profit_color}${self.gross_profit:,.2f}{end}\n"
            f"  \033[96mGross Loss{end}               {gross_loss_color}${self.gross_loss:,.2f}{end}\n"
            f"  {pf_color}Profit Factor{end}             {self.profit_factor:,.2f}\n"
            f"  \033[96mAverage Win{end}              {avg_win_color}${self.avg_win:,.2f}{end}\n"
            f"  \033[96mAverage Loss{end}             {avg_loss_color}${self.avg_loss:,.2f}{end}\n"
            f"\n\033[95m\033[1m⚠️ RISK METRICS{end}\n"
            f"  \033[96mMax Drawdown{end}             {gross_loss_color}${-self.max_drawdown:,.2f}{end}\n"
            f"  \033[96mPeak equity{end}              {gross_profit_color}${self.peak_equity:,.2f}{end}\n"
            f"  \033[96mSharpe Ratio{end}             {self.sharpe_ratio:,.2f}\n"
            f"  \033[96mMax Single Win{end}           {max_win_color}${self.max_win:,.2f}{end}\n"
            f"  \033[96mMax Single Loss{end}          {max_loss_color}${self.max_loss:,.2f}{end}\n"
            f"  \033[96mMax Win Streak{end}           {self.max_win_streak:,}\n"
            f"  \033[96mMax Loss Streak{end}          {self.max_loss_streak:,}\n"
            f"\n\033[95m\033[1m💸 TRADING COSTS{end}\n"
            f"  \033[96mTotal Fees Paid{end}          {fees_color}${self.fees_paid:,.2f}{end}\n"
            f"\n{'=' * 50}"
        )


class BaseBacktester():
    def __init__(self, position_manager: BasePositionManager):
        self.position_manager = position_manager
        self.stats = BaseBacktestStats()
        self.w_streak = 0
        self.l_streak = 0
        self.peak_equity = 0.0
        
        # store rolling realized PnL for Sharpe ratio
        self._MAX_LEN = 100
        self._pnl_history = np.zeros(self._MAX_LEN) 
        self._pos = 0
        # _________________________________________

            
    def update(self, candle: BaseCandle) -> None:
        
        # Cache frequently accessed objects in locals (major optimization)
        pos = self.position_manager.position
        stats = self.stats
        pm = self.position_manager
        
        # Update PnL and price
        stats.pnl = pm.get_unrealized_pnl(candle)
        stats.current_price = candle.close
        stats.current_position_info = pm.get_current_position_info() or {}

        # Handle open position
        pos_qty = pos.qty if pos else 0
        if pos_qty > 0:
            # Cache candle values and position side
            c_high = candle.high
            c_low = candle.low
            pos_side = pos.side
            is_long = pos_side == pos_side.LONG
            
            # Take-Profit handling
            tp_list = pos.tp
            tp_len = len(tp_list)
            if tp_len:
                tp_to_remove = []
                for idx in range(tp_len):
                    tp_price, tp_qty = tp_list[idx]
                    if (is_long and c_high >= tp_price) or (not is_long and c_low <= tp_price):
                        tp_to_remove.append(idx)
                        pm.record_tp_hit(candle, tp_price, tp_qty)
                        pm.set_hit_take_profit()
                        pm.close(candle, qty=tp_qty)
                        stats.exit_wins += 1
                
                for tp in tp_to_remove[::-1]:
                    tp_list.pop(tp)

            # Stop-Loss handling
            sl_list = pos.sl
            sl_len = len(sl_list)
            if sl_len:
                sl_to_remove = []
                for idx in range(sl_len):
                    sl_price, sl_qty = sl_list[idx]
                    if (is_long and c_low <= sl_price) or (not is_long and c_high >= sl_price):
                        sl_to_remove.append(idx)
                        pm.record_sl_hit(candle, sl_price, sl_qty)
                        pm.set_hit_stop_loss()
                        pm.close(candle, qty=sl_qty)
                        stats.exit_losses += 1
                
                for sl in sl_to_remove[::-1]:
                    sl_list.pop(sl)
                    
            # Check if position closed
            if pos.qty == 0:
                pos_pnl = pos.realized_pnl
                is_win = pos_pnl > 0
                
                # Update win/loss statistics
                if is_win:
                    stats.position_wins += 1
                    stats.gross_profit += pos_pnl
                    stats.max_win = max(stats.max_win, pos_pnl)
                    self.w_streak += 1
                    self.l_streak = 0
                    if is_long:
                        stats.long_wins += 1
                    else:
                        stats.short_wins += 1
                else:
                    stats.position_losses += 1
                    stats.gross_loss += pos_pnl
                    stats.max_loss = min(stats.max_loss, pos_pnl)
                    self.l_streak += 1
                    self.w_streak = 0

                # Calculate position duration
                entry_orders = pos.entry_orders
                exit_orders = pos.exit_orders
                if entry_orders and exit_orders:
                    duration = (exit_orders[-1].timestamp - entry_orders[0].timestamp).total_seconds() / 3600
                    stats.exposure_time += duration

                stats.max_win_streak = max(stats.max_win_streak, self.w_streak)
                stats.max_loss_streak = max(stats.max_loss_streak, self.l_streak)
                stats.total_pnl += pos_pnl

                # --- Update Sharpe ratio based on realized PnL changes ---
                self._pnl_history[pos % self._MAX_LEN] = self.stats.total_pnl
                self._pos += 1

                # --- Vectorized Sharpe ratio calculation ---
                if self._pos > 1:
                    # Take the filled portion of the PnL history
                    pnl_history = self._pnl_history[:min(self._pos, self._MAX_LEN)]

                    returns = np.diff(pnl_history) / np.abs(pnl_history[:-1])
                    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]

                    if returns.size > 1:
                        avg_return = returns.mean()
                        std_dev = returns.std(ddof=1)
                        self.stats.sharpe_ratio = (avg_return / std_dev) * np.sqrt(len(returns)) if std_dev > 0 else 0.0
                    else:
                        print("here")
                        self.stats.sharpe_ratio = 0.0


                self.stats.avg_win = self.stats.gross_profit / self.stats.position_wins if self.stats.position_wins > 0 else 0.0
                self.stats.avg_loss = self.stats.gross_loss / self.stats.position_losses if self.stats.position_losses > 0 else 0.0

        # Update general stats - cache values to reduce divisions
        positions = pm.position_count
        stats.positions = positions
        stats.fees_paid = pm.total_fees
        
        total_exits = stats.exit_wins + stats.exit_losses
        stats.exit_winrate = stats.exit_wins / total_exits if total_exits else 0.0
        
        gross_loss = stats.gross_loss
        stats.profit_factor = stats.gross_profit / -gross_loss if gross_loss < 0 else float('inf')
        
        longs = pm.total_longs
        stats.longs = longs
        stats.long_winrate = stats.long_wins / longs if longs else 0.0
        
        shorts = pm.total_shorts
        stats.shorts = shorts
        stats.short_winrate = stats.short_wins / shorts if shorts else 0.0
        
        stats.position_winrate = stats.position_wins / positions if positions else 0.0
        
        exposure = stats.exposure_time
        stats.position_frquency = positions / exposure if exposure else 0.0
        stats.avg_position_pnl = stats.total_pnl / positions if positions else 0.0
        stats.avg_position_duration = exposure / positions if positions else 0.0

        # Update equity and drawdown
        equity = self.stats.pnl + self.stats.total_pnl
        self.stats.equity = equity
        self.stats.peak_equity = max(self.peak_equity, equity)
        drawdown = self.stats.peak_equity - equity
        self.stats.max_drawdown = max(self.stats.max_drawdown, drawdown)


    def get_recent_position_events(self):
        """Get recent position events for plotting."""
        return self.position_manager.get_recent_events()

    def get_all_position_events(self):
        """Get all position events for plotting."""
        return self.position_manager.get_all_events()

    def get_results(self) -> dict:
        return asdict(self.stats)
        
    def __str__(self) -> str:
        return str(self.stats)