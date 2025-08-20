from core.base_strategy import BaseStrategy
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

    def __str__(self):
        stats = asdict(self)
        lines = []

        for key, value in stats.items():
            # pick color by stat type
            if isinstance(value, (int, float)):
                if key in ["pnl", "total_pnl", "gross_profit", "avg_win", "max_win"]:
                    color = Fore.GREEN if value >= 0 else Fore.RED
                elif key in ["gross_loss", "avg_loss", "max_loss", "max_drawdown"]:
                    color = Fore.RED
                elif "winrate" in key or "factor" in key:
                    color = Fore.CYAN
                else:
                    color = Fore.YELLOW
                lines.append(f"{key:22}: {color}{value}{Style.RESET_ALL}")
            else:
                # non-numeric entries (lists, dicts, etc.)
                color = Fore.MAGENTA
                if isinstance(value, list):
                    display = f"[len={len(value)}]"
                else:
                    display = str(value)
                lines.append(f"{key:22}: {color}{display}{Style.RESET_ALL}")

        return "\n".join(lines)


class BaseBacktester(BaseSubscriber):
    def __init__(self,data_provider: BaseDataProvider, position_manager: BasePositionManager):
        self.data_provider = data_provider
        self.position_manager = position_manager
        self.data_provider.subscribe(self)
        self.stats = BaseBacktestStats()
        self.w_streak = 0
        self.l_streak = 0

    def update(self, candle: BaseCandle) -> None:
        pos = self.position_manager.position

        # Handle open position: TP, SL, Liquidation
        if pos and pos.qty > 0:
            self.stats.pnl = self.position_manager.get_unrealized_pnl(candle)
            self.stats.equity_curve.append(self.stats.pnl + self.stats.total_pnl)
            self.stats.max_drawdown = min(self.stats.max_drawdown, self.stats.pnl + self.stats.total_pnl)

            # Take-Profit
            for tp_price, tp_percent in pos.tp:
                if (pos.side == pos.side.LONG and candle.high >= tp_price) or \
                   (pos.side == pos.side.SHORT and candle.low <= tp_price):
                    self.position_manager.set_hit_take_profit()
                    self.position_manager.close(candle, percentage=tp_percent)
                    self.stats.exit_wins += 1
                    self.stats.position_history.append({'type': 'tp', 'price': tp_price, 'candle': candle})
                    return

            # Stop-Loss
            for sl_price, sl_percent in pos.sl:
                if (pos.side == pos.side.LONG and candle.low <= sl_price) or \
                   (pos.side == pos.side.SHORT and candle.high >= sl_price):
                    self.position_manager.set_hit_stop_loss()
                    self.position_manager.close(candle, percentage= sl_percent)
                    self.stats.exit_losses += 1
                    self.stats.position_history.append({'type': 'sl', 'price': sl_price, 'candle': candle})
                    return
                
            # Check if positon is closed
            if pos.qty == 0:
                # Check if position is a win
                if pos.realized_pnl > 0:
                    self.stats.position_wins += 1
                    self.stats.gross_profit += pos.realized_pnl
                    self.stats.max_win = max(self.stats.max_win, self.stats.pnl)
                    self.w_streak += 1
                    self.l_streak = 0
                    if pos.side == pos.side.LONG:
                        self.stats.long_wins += 1
                    elif pos.side == pos.side.SHORT:
                        self.stats.short_wins += 1
                else:
                    self.stats.position_losses += 1
                    self.stats.gross_loss += pos.realized_pnl
                    self.stats.max_loss = max(self.stats.max_loss, self.stats.pnl)
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
                self.stats.total_pnl += self.stats.pnl
                self.stats.avg_win = self.stats.gross_profit / self.stats.position_wins if self.stats.exit_wins > 0 else 0.0
                self.stats.avg_loss = self.stats.gross_loss / self.stats.position_losses if self.stats.exit_losses > 0 else 0.0


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
        self.stats.positions = self.position_manager.position_count
        self.stats.fees_paid = self.position_manager.total_fees
        self.stats.exit_winrate = (self.stats.exit_wins / (self.stats.exit_wins + self.stats.exit_losses)) if self.stats.positions > 0 else 0.0
        self.stats.profit_factor = (self.stats.gross_profit / abs(self.stats.gross_loss)) if self.stats.gross_loss < 0 else float('inf')
        self.stats.longs = self.position_manager.total_longs
        self.stats.long_winrate = (self.stats.long_wins / self.stats.longs) if self.stats.longs > 0 else 0.0
        self.stats.shorts = self.position_manager.total_shorts
        self.stats.short_winrate = (self.stats.short_wins / self.stats.shorts) if self.stats.shorts > 0 else 0.0
        self.stats.position_winrate = (self.stats.position_wins / self.stats.positions) if self.stats.positions > 0 else 0.0
        self.stats.position_frquency = self.stats.positions / self.stats.exposure_time if self.stats.exposure_time > 0 else 0.0
        self.stats.avg_position_pnl = self.stats.total_pnl / self.stats.positions if self.stats.positions > 0 else 0.0

        return asdict(self.stats)
    
        
    def __str__(self) -> str:
        return str(self.stats)
