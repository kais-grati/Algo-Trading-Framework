import json
from pathlib import Path
from core.position import Position, Order, PositionSide, PositionStatus
from data.base_candle import BaseCandle
from typing import List, Optional, Tuple, Dict, Any
from uuid import uuid4
from dataclasses import asdict
from collections import deque
from datetime import datetime

class BasePositionManager:
    def __init__(self, log_path: Optional[str] = None, event_history_size: int = 100):
        self.position: Optional[Position] = None
        self.log_path = Path(log_path) if log_path else Path(__file__).parent / "position_log.json"
        self.log_path.write_text(json.dumps({"orders": [], "closed_positions": []}))
        self.position_count = 0
        self.total_fees = 0.0
        self.total_longs = 0
        self.total_shorts = 0
        
        # Event tracking for plotting
        self.all_events = []  # Complete history of all events
        self.recent_events = deque(maxlen=event_history_size)  # Recent events buffer for plotting
        self.event_counter = 0

    def _log_order(self, order: Order):
        log = json.loads(self.log_path.read_text())
        log["orders"].append(asdict(order))
        self.log_path.write_text(json.dumps(log, default=str, indent=2))

    def _log_closed_position(self, position: Position):
        log = json.loads(self.log_path.read_text())
        log["closed_positions"].append(asdict(position))
        self.log_path.write_text(json.dumps(log, default=str, indent=2))

    def _create_event(self, event_type: str, candle: BaseCandle, **kwargs) -> Dict[str, Any]:
        """Create a standardized event dictionary."""
        self.event_counter += 1
        event = {
            'id': self.event_counter,
            'timestamp': candle.timestamp if hasattr(candle, 'timestamp') else datetime.now(),
            'event_type': event_type,
            'price': candle.close,
            'candle_data': {
                'open': candle.open,
                'high': candle.high,
                'low': candle.low,
                'close': candle.close,
                'volume': getattr(candle, 'volume', 0)
            }
        }
        
        # Add position info if available
        if self.position:
            event['position_info'] = {
                'side': self.position.side.name,
                'quantity': self.position.qty,
                'avg_price': self.position.avg_price,
                'unrealized_pnl': self.position.compute_upnl(candle.close)
            }
        
        # Add any additional kwargs
        event.update(kwargs)
        
        return event

    def _record_event(self, event: Dict[str, Any]):
        """Record an event in both all_events and recent_events."""
        self.all_events.append(event)
        self.recent_events.append(event)

    def long(self, candle: BaseCandle, value: Optional[float] = None, qty: Optional[float] = None, tp: List[Tuple[float, float]] = [], sl: List[Tuple[float, float]] = [], fees: float = 0) -> None:
        """
        Open or increase a long position.
        Order can be placed either using monetary value (ie. 200$) => value param. or using asset quantity (ie. 2 BTC) => qty param.
        For tp and sl the format of the tuples should be (trigger_price, percent)
        """
        if value:
            quantity = value / candle.close
        elif qty:
            quantity = qty
        else:
            print("Can't place an order without specifying quantity or value")
            return
            
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=quantity,
            fees=fees
        )
        self.total_fees = self.total_fees + fees
        
        if self.position is not None:
            if self.position.side == PositionSide.LONG:
                # Increase existing long position
                self.position.apply_fill(order, is_entry=True)
                self._log_order(order)
                
                # Record increase long event
                event = self._create_event('increase_long', candle, 
                                         quantity=quantity, 
                                         value=value, 
                                         fees=fees,
                                         order_id=order.order_id)
                self._record_event(event)
                return
            else:
                print("A position of opposite side is already open.")
                return
        # Convert tp/sl percentages into quantity
        tp = [(price, percent * quantity) for price, percent in tp]
        sl = [(price, percent * quantity) for price, percent in sl]

        
        pos = Position.long(tp=tp, sl=sl)
        pos.apply_fill(order, is_entry=True)
        self.position = pos
        self._log_order(order)
        self.total_longs += 1
        self.position_count += 1
        
        # Record open long event
        event = self._create_event('open_long', candle, 
                                 quantity=quantity, 
                                 value=value, 
                                 fees=fees,
                                 take_profit_levels=len(tp),
                                 stop_loss_levels=len(sl),
                                 order_id=order.order_id)
        self._record_event(event)

    def short(self, candle: BaseCandle, value: Optional[float] = None, qty: Optional[float] = None, tp: List[Tuple[float, float]] = [], sl: List[Tuple[float, float]] = [], fees: float = 0) -> None:
        """
        Open or increase a short position.
        Order can be placed either using monetary value (ie. 200$) => value param. or using asset quantity (ie. 2 BTC) => qty param.
        """
        if value:
            quantity = value / candle.close
        elif qty:
            quantity = qty
        else:
            print("Can't place an order without specifying quantity or value")
            return
            
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=quantity,
            fees=fees
        )
        self.total_fees = self.total_fees + fees

        if self.position is not None:
            if self.position.side == PositionSide.SHORT:
                # Increase existing short position
                self.position.apply_fill(order, is_entry=True)
                self._log_order(order)
                
                # Record increase short event
                event = self._create_event('increase_short', candle, 
                                         quantity=quantity, 
                                         value=value, 
                                         fees=fees,
                                         order_id=order.order_id)
                self._record_event(event)
                return
            else:
                print("A position of opposite side is already open.")
                return
            
        # Convert tp/sl percentages into quantity
        tp = [(price, percent * quantity) for (price, percent) in tp]
        sl = [(price, percent * quantity) for (price, percent) in sl]

        pos = Position.short(tp=tp, sl=sl)
        pos.apply_fill(order, is_entry=True)
        self.position = pos
        self._log_order(order)
        self.total_shorts += 1
        self.position_count += 1
        
        # Record open short event
        event = self._create_event('open_short', candle, 
                                 quantity=quantity, 
                                 value=value, 
                                 fees=fees,
                                 take_profit_levels=len(tp),
                                 stop_loss_levels=len(sl),
                                 order_id=order.order_id)
        self._record_event(event)

    def close(self, candle: BaseCandle, qty: Optional[float] = None, percentage: Optional[float] = None) -> None:
        """Close the current position, fully or by quantity/percentage."""
        if self.position is None or self.position.qty == 0:
            return
        
        original_qty = self.position.qty
        
        if qty is not None:
            close_qty = min(qty, self.position.qty)
        elif percentage is not None:
            close_qty = self.position.qty * min(max(percentage, 0.0), 1.0)
        else:
            close_qty = self.position.qty 
            
        if close_qty <= 0:
            print("Close quantity must be positive.")
            return
        
        order = Order(
            order_id=str(uuid4()),
            price=candle.close,
            quantity=close_qty
        )
        
        # Calculate PnL before closing
        pnl_before_close = self.position.compute_upnl(candle.close)
        
        self.position.apply_fill(order, is_entry=False)
        self._log_order(order)
        
        # Determine if this is a full or partial close
        is_full_close = self.position.qty == 0
        event_type = 'close_full' if is_full_close else 'close_partial'
        
        # Record close event
        event = self._create_event(event_type, candle, 
                                 quantity=close_qty, 
                                 percentage=percentage,
                                 was_full_position=original_qty == close_qty,
                                 unrealized_pnl_at_close=pnl_before_close,
                                 order_id=order.order_id)
        self._record_event(event)

        if self.position.qty == 0:
            self._log_closed_position(self.position)
            self.position = None

    def record_tp_hit(self, candle: BaseCandle, tp_price: float, tp_qty: float):
        """Record a take-profit hit event."""
        event = self._create_event('tp_hit', candle, 
                                 tp_price=tp_price, 
                                 tp_quantity=tp_qty,
                                 trigger_price=tp_price)
        self._record_event(event)

    def record_sl_hit(self, candle: BaseCandle, sl_price: float, sl_qty: float):
        """Record a stop-loss hit event."""
        event = self._create_event('sl_hit', candle, 
                                 sl_price=sl_price, 
                                 sl_quantity=sl_qty,
                                 trigger_price=sl_price)
        self._record_event(event)

    def get_unrealized_pnl(self, candle: BaseCandle) -> float:
        """Get unrealized PnL for the open position."""
        if self.position is None:
            return 0.0
        return self.position.compute_upnl(candle.close)

    def get_current_position_info(self) -> Optional[Dict[str, Any]]:
        """Get current position information for plotting."""
        if self.position is None or self.position.qty == 0:
            return None
            
        return {
            'side': self.position.side.name,
            'quantity': self.position.qty,
            'avg_price': self.position.avg_price,
            'total_fees': self.position.total_fees,
            'realized_pnl': self.position.realized_pnl,
            'take_profit_levels': len(self.position.tp),
            'stop_loss_levels': len(self.position.sl),
            'tp_orders': [{'price': price, 'quantity': qty} for price, qty in self.position.tp],
            'sl_orders': [{'price': price, 'quantity': qty} for price, qty in self.position.sl],
            'entry_orders_count': len(self.position.entry_orders),
            'exit_orders_count': len(self.position.exit_orders),
            'reached_tp': getattr(self.position, 'reached_tp', False),
            'reached_sl': getattr(self.position, 'reached_sl', False)
        }

    def get_recent_events(self) -> List[Dict[str, Any]]:
        """Get recent events for plotting."""
        return list(self.recent_events)

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Get all recorded events."""
        return self.all_events.copy()

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [event for event in self.all_events if event['event_type'] == event_type]

    def get_events_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get events within a specific timeframe."""
        return [
            event for event in self.all_events 
            if start_time <= event['timestamp'] <= end_time
        ]

    def clear_recent_events(self):
        """Clear the recent events buffer."""
        self.recent_events.clear()

    @property
    def has_position(self) -> bool:
        return self.position is not None and self.position.qty != 0
    
    def set_hit_take_profit(self) -> None:
        """Set a take-profit flag for the current position."""
        if self.position is None:
            return
        self.position.reached_tp = True
    
    def set_hit_stop_loss(self) -> None:
        """Set a stop-loss flag for the current position."""
        if self.position is None:
            return
        self.position.reached_sl = True

    def get_position_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about position events."""
        stats = {
            'total_events': len(self.all_events),
            'event_types': {},
            'total_positions_opened': 0,
            'total_positions_closed': 0,
            'tp_hits': 0,
            'sl_hits': 0,
            'position_increases': 0
        }
        
        for event in self.all_events:
            event_type = event['event_type']
            stats['event_types'][event_type] = stats['event_types'].get(event_type, 0) + 1
            
            if event_type in ['open_long', 'open_short']:
                stats['total_positions_opened'] += 1
            elif event_type in ['close_full']:
                stats['total_positions_closed'] += 1
            elif event_type == 'tp_hit':
                stats['tp_hits'] += 1
            elif event_type == 'sl_hit':
                stats['sl_hits'] += 1
            elif event_type in ['increase_long', 'increase_short']:
                stats['position_increases'] += 1
        
        return stats

    def export_events(self, filename: str = "position_events.json"):
        """Export all events to a JSON file."""
        export_data = {
            'total_events': len(self.all_events),
            'statistics': self.get_position_statistics(),
            'events': self.all_events
        }
        
        Path(filename).write_text(json.dumps(export_data, default=str, indent=2))
        print(f"Position events exported to {filename}")