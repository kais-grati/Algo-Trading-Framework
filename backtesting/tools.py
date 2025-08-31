import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from datetime import datetime

class MeasureTool:
    def __init__(self, plot_widget):
        self.plot_widget = plot_widget
        self.is_measuring = False
        self.first_point = None
        self.second_point = None
        self.measure_line = None
        self.measure_text = None
        self.measure_rectangle = None  # Track final rectangle
        self.temp_line = None
        self.temp_rectangle = None
        self.temp_text = None
        self.measure_button = None
        self.crosshairs = []  # Track crosshair markers for proper cleanup
        
    def toggle_measure_mode(self):
        """Toggle measure mode on/off"""
        self.is_measuring = not self.is_measuring
        
        if self.is_measuring:
            self.start_measuring()
        else:
            self.stop_measuring()
    
    def start_measuring(self):
        """Start measure mode"""
        self.clear_measure()
        
        # Connect to mouse events - use the plot widget's view box for better accuracy
        view_box = self.plot_widget.getViewBox()
        view_box.scene().sigMouseClicked.connect(self.on_mouse_click)
        view_box.scene().sigMouseMoved.connect(self.on_mouse_move)
        
        # Change cursor to crosshair
        self.plot_widget.setCursor(QtCore.Qt.CursorShape.CrossCursor)
        
        # Update button text
        if self.measure_button:
            self.measure_button.setText("Cancel Measure")
            self.measure_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff6666;
                }
            """)
    
    def stop_measuring(self):
        """Stop measure mode"""
        try:
            view_box = self.plot_widget.getViewBox()
            view_box.scene().sigMouseClicked.disconnect(self.on_mouse_click)
            view_box.scene().sigMouseMoved.disconnect(self.on_mouse_move)
        except:
            pass
        
        # Reset cursor
        self.plot_widget.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        
        # Clear temporary elements
        self.clear_temp_elements()
        
        # Update button text
        if self.measure_button:
            self.measure_button.setText("Measure Tool")
            self.measure_button.setStyleSheet("""
                QPushButton {
                    background-color: #0077ff;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0099ff;
                }
            """)
    
    def on_mouse_click(self, event):
        """Handle mouse clicks for measuring"""
        if not self.is_measuring:
            return
        
        # Only handle left mouse button clicks
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        
        # Get click position in data coordinates
        view_box = self.plot_widget.getViewBox()
        scene_pos = event.scenePos()
        
        # Check if click is within the plot area
        if view_box.sceneBoundingRect().contains(scene_pos):
            # Map scene coordinates to view coordinates (data coordinates)
            mouse_point = view_box.mapSceneToView(scene_pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            if self.first_point is None:
                # First click - set starting point
                self.first_point = (x, y)
                crosshair = self.add_crosshair(x, y, '#00ff00')  # Green crosshair
                self.crosshairs.append(crosshair)
                
            else:
                # Second click - complete measurement
                self.second_point = (x, y)
                crosshair = self.add_crosshair(x, y, '#ff0000')  # Red crosshair
                self.crosshairs.append(crosshair)
                self.complete_measurement()
                self.stop_measuring()
    
    def on_mouse_move(self, pos):
        """Handle mouse movement for temporary line preview with TradingView-style rectangle"""
        if not self.is_measuring or self.first_point is None:
            return
        
        view_box = self.plot_widget.getViewBox()
        
        # Check if mouse is within the plot area
        if view_box.sceneBoundingRect().contains(pos):
            # Map scene coordinates to view coordinates (data coordinates)
            mouse_point = view_box.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            # Clear previous temporary elements
            self.clear_temp_elements()
            
            # Calculate measurements
            x1, y1 = self.first_point
            price_diff = y - y1
            percent_change = ((y - y1) / y1) * 100 if y1 != 0 else 0
            time_diff = abs(x - x1) / 3600  # Convert to hours
            
            # Create TradingView-style rectangle
            rect_x = min(x1, x)
            rect_y = min(y1, y)
            rect_width = abs(x - x1)
            rect_height = abs(y - y1)
            
            # Determine color based on price movement
            is_positive = y >= y1
            fill_color = (0, 255, 136, 40) if is_positive else (255, 68, 68, 40)  # Semi-transparent
            border_color = '#00ff88' if is_positive else '#ff4444'
            
            # Create transparent rectangle
            self.temp_rectangle = pg.QtWidgets.QGraphicsRectItem(
                rect_x, rect_y, rect_width, rect_height
            )
            self.temp_rectangle.setPen(pg.mkPen(color=border_color, width=1, style=QtCore.Qt.PenStyle.DashLine))
            self.temp_rectangle.setBrush(pg.mkBrush(color=fill_color))
            self.plot_widget.addItem(self.temp_rectangle)
            
            # Create diagonal line from corner to corner
            self.temp_line = pg.PlotDataItem(
                x=[x1, x],
                y=[y1, y],
                pen=pg.mkPen(color=border_color, width=2, style=QtCore.Qt.PenStyle.SolidLine)
            )
            self.plot_widget.addItem(self.temp_line)
            
            # Create live measurement text box (TradingView style)
            measurement_text = self.format_live_measurement(price_diff, percent_change, time_diff, y1, y)
            
            # Position text box near the current mouse position, but offset to avoid overlap
            text_x = x + (rect_width * 0.1)  # Slightly offset from mouse
            text_y = y + (rect_height * 0.1)
            
            # Create text with background box
            self.temp_text = pg.TextItem(
                html=measurement_text,
                anchor=(0, 1),  # Top-left anchor
                border=pg.mkPen(color=border_color, width=1),
                fill=pg.mkBrush(color=(30, 30, 30, 200))  # Semi-transparent dark background
            )
            self.temp_text.setPos(text_x, text_y)
            self.plot_widget.addItem(self.temp_text)
    
    def format_live_measurement(self, price_diff, percent_change, time_diff, start_price, end_price):
        """Format the live measurement text in TradingView style"""
        # Determine colors
        is_positive = price_diff >= 0
        change_color = '#00ff88' if is_positive else '#ff4444'
        
        # Format the HTML text
        html_text = f"""
        <div style="color: #ffffff; font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; padding: 8px;">
            <div style="color: #888888; font-size: 10px; margin-bottom: 4px;">MEASURE</div>
            <div style="margin-bottom: 2px;">
                <span style="color: #cccccc;">From:</span> 
                <span style="color: #ffffff; font-weight: bold;">${start_price:.2f}</span>
            </div>
            <div style="margin-bottom: 2px;">
                <span style="color: #cccccc;">To:</span> 
                <span style="color: #ffffff; font-weight: bold;">${end_price:.2f}</span>
            </div>
            <div style="margin-bottom: 2px;">
                <span style="color: #cccccc;">Change:</span> 
                <span style="color: {change_color}; font-weight: bold;">{price_diff:+.2f} ({percent_change:+.2f}%)</span>
            </div>
            <div style="color: #888888; font-size: 10px;">
                Time: {time_diff:.1f}h
            </div>
        </div>
        """
        return html_text
    
    def clear_temp_elements(self):
        """Clear all temporary visual elements"""
        if self.temp_line:
            self.plot_widget.removeItem(self.temp_line)
            self.temp_line = None
        
        if self.temp_rectangle:
            self.plot_widget.removeItem(self.temp_rectangle)
            self.temp_rectangle = None
        
        if self.temp_text:
            self.plot_widget.removeItem(self.temp_text)
            self.temp_text = None
    
    def add_crosshair(self, x, y, color):
        """Add a crosshair marker at the specified point"""
        scatter = pg.ScatterPlotItem(
            x=[x], y=[y],
            pen=pg.mkPen(color=color, width=2),
            brush=pg.mkBrush(color=color),
            symbol='+',
            size=15
        )
        self.plot_widget.addItem(scatter)
        return scatter
    
    def complete_measurement(self):
        """Complete the measurement and display final results"""
        if not self.first_point or not self.second_point:
            return
        
        x1, y1 = self.first_point
        x2, y2 = self.second_point
        
        # Calculate measurements
        price_diff = y2 - y1
        percent_change = ((y2 - y1) / y1) * 100 if y1 != 0 else 0
        time_diff = abs(x2 - x1) / 3600  # Convert seconds to hours
        
        # Clear temporary elements
        self.clear_temp_elements()
        
        # Determine color based on change
        is_positive = percent_change >= 0
        line_color = '#00ff88' if is_positive else '#ff4444'
        fill_color = (0, 255, 136, 40) if is_positive else (255, 68, 68, 40)
        
        # Create final rectangle
        rect_x = min(x1, x2)
        rect_y = min(y1, y2)
        rect_width = abs(x2 - x1)
        rect_height = abs(y2 - y1)
        
        self.measure_rectangle = pg.QtWidgets.QGraphicsRectItem(
            rect_x, rect_y, rect_width, rect_height
        )
        self.measure_rectangle.setPen(pg.mkPen(color=line_color, width=1, style=QtCore.Qt.PenStyle.SolidLine))
        self.measure_rectangle.setBrush(pg.mkBrush(color=fill_color))
        self.plot_widget.addItem(self.measure_rectangle)
        
        # Add diagonal line
        self.measure_line = pg.PlotDataItem(
            x=[x1, x2],
            y=[y1, y2],
            pen=pg.mkPen(color=line_color, width=2)
        )
        self.plot_widget.addItem(self.measure_line)
        
        # Add final measurement text (more prominent than temp text)
        final_text = self.format_final_measurement(price_diff, percent_change, time_diff, y1, y2)
        
        # Position text at rectangle center
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        self.measure_text = pg.TextItem(
            html=final_text,
            anchor=(0.5, 0.5),  # Center anchor
            border=pg.mkPen(color=line_color, width=2),
            fill=pg.mkBrush(color=(20, 20, 20, 220))  # More opaque background
        )
        self.measure_text.setPos(mid_x, mid_y)
        self.plot_widget.addItem(self.measure_text)
    
    def format_final_measurement(self, price_diff, percent_change, time_diff, start_price, end_price):
        """Format the final measurement text in TradingView style"""
        is_positive = price_diff >= 0
        change_color = '#00ff88' if is_positive else '#ff4444'
        arrow = '▲' if is_positive else '▼'
        
        html_text = f"""
        <div style="color: #ffffff; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; padding: 10px; text-align: center;">
            <div style="color: {change_color}; font-size: 14px; font-weight: bold; margin-bottom: 4px;">
                {arrow} {percent_change:+.2f}%
            </div>
            <div style="color: {change_color}; font-weight: bold; margin-bottom: 2px;">
                ${price_diff:+.2f}
            </div>
            <div style="color: #888888; font-size: 10px; margin-bottom: 1px;">
                From: ${start_price:.2f}
            </div>
            <div style="color: #888888; font-size: 10px; margin-bottom: 3px;">
                To: ${end_price:.2f}
            </div>
            <div style="color: #888888; font-size: 9px;">
                {time_diff:.1f} hours
            </div>
        </div>
        """
        return html_text
    
    def clear_measure(self):
        """Clear all measurement elements"""
        # Clear final measurement elements
        if self.measure_line:
            self.plot_widget.removeItem(self.measure_line)
            self.measure_line = None
        
        if self.measure_text:
            self.plot_widget.removeItem(self.measure_text)
            self.measure_text = None
            
        if self.measure_rectangle:
            self.plot_widget.removeItem(self.measure_rectangle)
            self.measure_rectangle = None
        
        # Clear temporary elements
        self.clear_temp_elements()
        
        # Clear all crosshairs
        for crosshair in self.crosshairs:
            self.plot_widget.removeItem(crosshair)
        self.crosshairs.clear()
        
        # Reset points
        self.first_point = None
        self.second_point = None