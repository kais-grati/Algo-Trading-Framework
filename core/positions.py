from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from datetime import datetime
from typing import List, Optional, Tuple


class PositionSide(Enum):
    LONG = auto()
    SHORT = auto()

class PositionStatus(Enum):
    OPEN = auto()
    CLOSED = auto()


@dataclass
class Order:
    order_id: str
    price: float
    quantity: float 
    timestamp: datetime = field(default_factory=datetime.now)
    fees: float = 0.0

@dataclass
class Position:
    side: PositionSide
    qty: float = 0.0
    avg_price: float = 0.0
    total_fees: float = 0.0
    state: PositionStatus = PositionStatus.OPEN
    entry_orders: List[Order] = field(default_factory=list)
    exit_orders: List[Order] = field(default_factory=list)
    realized_pnl: float = 0.0
    tp: List[Tuple[float, float]] = field(default_factory=list)  # List of (price, %) tuples for take-profit orders
    sl: List[Tuple[float, float]] = field(default_factory=list)  # List of (price, %) tuples for stop-loss orders
    reached_tp: bool = False
    reached_sl: bool = False

    def apply_fill(self, order: Order, is_entry: bool = True) -> None:
        """Update position with an order (entry or exit)."""
        self.total_fees += order.fees
        if is_entry:
            # update weighted average
            total_cost = self.avg_price * self.qty + order.price * order.quantity
            self.qty += order.quantity
            self.avg_price = total_cost / self.qty if self.qty else 0.0
            self.entry_orders.append(order)
        else:
            # reduce/close -> compute realized pnl
            closed_qty = min(self.qty, order.quantity)
            pnl = (order.price - self.avg_price) * closed_qty
            if self.side == PositionSide.SHORT:
                pnl = -pnl
            self.realized_pnl += pnl - order.fees
            self.qty -= closed_qty
            self.exit_orders.append(order)
            if self.qty <= 0:
                self.state = PositionStatus.CLOSED
                self.qty = 0.0

    def compute_upnl(self, market_price: float) -> float:
        """Return unrealized PnL against market price (not changing state)."""
        if self.qty == 0:
            return 0.0
        unreal = (market_price - self.avg_price) * self.qty
        if self.side == PositionSide.SHORT:
            unreal = -unreal
        return unreal
    
    @staticmethod
    def short(tp: Optional[List[Tuple[float, float]]] = None,
              sl: Optional[List[Tuple[float, float]]] = None) -> Position:
        kwargs = {}
        if tp is not None:
            kwargs["tp"] = tp
        if sl is not None:
            kwargs["sl"] = sl

        return Position(
            side=PositionSide.SHORT,
            qty=0.0,
            avg_price=0.0,
            **kwargs
        )
    
    @staticmethod
    def long(tp: Optional[List[Tuple[float, float]]] = None,
              sl: Optional[List[Tuple[float, float]]] = None) -> Position:
        kwargs = {}
        if tp is not None:
            kwargs["tp"] = tp
        if sl is not None:
            kwargs["sl"] = sl

        return Position(
            side=PositionSide.LONG,
            qty=0.0,
            avg_price=0.0,
            **kwargs
        )