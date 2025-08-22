import json
from pathlib import Path
from core.positions import Position, Order, PositionSide, PositionStatus
from data.base_candle import BaseCandle
from typing import List, Optional, Tuple
from uuid import uuid4
from dataclasses import asdict

class BasePositionManager:
    def __init__(self, log_path: Optional[str] = None):
        self.position: Optional[Position] = None
        self.closed_positions: List[Position] = []
        self.log_path = Path(log_path) if log_path else Path(__file__).parent / "position_log.json"
        self.log_path.write_text(json.dumps({"orders": [], "closed_positions": []}))
        self.position_count = 0
        self.total_fees = 0.0
        self.total_longs = 0
        self.total_shorts = 0

    def _log_order(self, order: Order):
        log = json.loads(self.log_path.read_text())
        log["orders"].append(asdict(order))
        self.log_path.write_text(json.dumps(log, default=str, indent=2))

    def _log_closed_position(self, position: Position):
        log = json.loads(self.log_path.read_text())
        log["closed_positions"].append(asdict(position))
        self.log_path.write_text(json.dumps(log, default=str, indent=2))

    def long(self, candle: BaseCandle, qty: float, tp: List[Tuple[float, float]] = [], sl: List[Tuple[float, float]] = [], fees: float = 0) -> None:
        """Open or increase a long position."""
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=qty,
            fees=fees
        )
        self.total_fees = self.total_fees + fees
        if self.position is not None:
            if self.position.side == PositionSide.LONG:
                # Increase existing long position
                self.position.apply_fill(order, is_entry=True)
                self._log_order(order)
                return
            else:
                raise ValueError("A position of opposite side is already open.")
        pos = Position(
            side=PositionSide.LONG,
            qty=0.0,
            avg_price=0.0,
            tp=tp,
            sl=sl
        )
        
        pos.apply_fill(order, is_entry=True)
        self.position = pos
        self._log_order(order)
        self.total_longs += 1
        self.position_count += 1


    def short(self, candle: BaseCandle, qty: float, tp: List[Tuple[float, float]] = [], sl: List[Tuple[float, float]] = [], fees: float = 0) -> None:
        """Open or increase a short position."""
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=qty,
            fees=fees
        )
        self.total_fees = self.total_fees + fees

        if self.position is not None:
            if self.position.side == PositionSide.SHORT:
                # Increase existing short position
                self.position.apply_fill(order, is_entry=True)
                self._log_order(order)
                return
            else:
                raise ValueError("A position of opposite side is already open.")
        pos = Position(
            side=PositionSide.SHORT,
            qty=0.0,
            avg_price=0.0,
            tp=tp,
            sl=sl
        )
        pos.apply_fill(order, is_entry=True)
        self.position = pos
        self._log_order(order)
        self.total_shorts += 1
        self.position_count += 1

    def close(self, candle: BaseCandle, qty: Optional[float] = None, percentage: Optional[float] = None) -> None:
        """Close the current position, fully or by quantity/percentage."""
        if self.position is None or self.position.qty == 0:
            return
        
        if qty is not None:
            close_qty = min(qty, self.position.qty)
        elif percentage is not None:
            close_qty = self.position.qty * min(max(percentage, 0.0), 1.0)
        else:
            close_qty = self.position.qty 

        if close_qty <= 0:
            raise ValueError("Close quantity must be positive.")

        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=close_qty
        )
        self.position.apply_fill(order, is_entry=False)
        self._log_order(order)

        if self.position.qty == 0:
            self.closed_positions.append(self.position)
            self._log_closed_position(self.position)
            self.position = None

    def get_unrealized_pnl(self, candle: BaseCandle) -> float:
        """Get unrealized PnL for the open position."""
        if self.position is None:
            return 0.0
        return self.position.compute_upnl(candle.close)

    @property
    def has_position(self) -> bool:
        return self.position is not None and self.position.qty != 0
    
    def set_hit_take_profit(self) -> None:
        """Set a take-profit order for the current position."""
        if self.position is None:
            return
        self.position.reached_tp = True
    
    def set_hit_stop_loss(self) -> None:
        """Set a take-profit order for the current position."""
        if self.position is None:
            return
        self.position.reached_sl = True