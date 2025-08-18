import json
from pathlib import Path
from core.positions import Position, Order, PositionSide, PositionStatus
from data.base_candle import BaseCandle
from typing import List, Optional
from uuid import uuid4
from dataclasses import asdict

class PositionManager:
    def __init__(self, log_path: Optional[str] = None):
        self.position: Optional[Position] = None
        self.closed_positions: List[Position] = []
        self.log_path = Path(log_path) if log_path else Path(__file__).parent / "position_log.json"
        if not self.log_path.exists():
            self.log_path.write_text(json.dumps({"orders": [], "closed_positions": []}))

    def _log_order(self, order: Order):
        log = json.loads(self.log_path.read_text())
        log["orders"].append(asdict(order))
        self.log_path.write_text(json.dumps(log, default=str, indent=2))

    def _log_closed_position(self, position: Position):
        log = json.loads(self.log_path.read_text())
        log["closed_positions"].append(asdict(position))
        self.log_path.write_text(json.dumps(log, default=str, indent=2))

    def long(self, candle: BaseCandle, qty: float) -> None:
        """Open or increase a long position."""
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=qty
        )
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
            avg_price=0.0
        )
        pos.apply_fill(order, is_entry=True)
        self.position = pos
        self._log_order(order)

    def short(self, candle: BaseCandle, qty: float) -> None:
        """Open or increase a short position."""
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=qty
        )
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
            avg_price=0.0
        )
        pos.apply_fill(order, is_entry=True)
        self.position = pos
        self._log_order(order)

    def close(self, candle: BaseCandle) -> None:
        """Close the current position."""
        if self.position is None or self.position.qty == 0:
            raise ValueError("No open position to close.")
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=self.position.qty
        )
        self.position.apply_fill(order, is_entry=False)
        self.closed_positions.append(self.position)
        self._log_order(order)
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