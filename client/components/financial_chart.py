# -*- coding: utf-8 -*-
"""Professional Financial Chart Component using Qt Graphs"""

from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QValueAxis, QBarCategoryAxis
from PySide6.QtCore import QMargins
from PySide6.QtGui import QPainter
from client.components.jalali_date import persian_month_name


class FinancialChart(QWidget):
    """Professional financial chart with Persian labels and values"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_data = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Chart title
        self.title_label = QLabel("روند مالی ۱۲ ماه اخیر")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background: transparent;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Create chart
        self.chart = QChart()
        self.chart.setTheme(QChart.ChartThemeLight)
        self.chart.setBackgroundBrush(Qt.white)
        self.chart.setMargins(QMargins(10, 10, 10, 10))
        
        # Chart view
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("""
            QChartView {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                background: white;
            }
        """)
        layout.addWidget(self.chart_view)
        
        # Legend frame
        legend_frame = QFrame()
        legend_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setSpacing(20)
        
        # Revenue legend
        revenue_legend = QLabel("🟢 درآمد")
        revenue_legend.setStyleSheet("color: #28a745; font-weight: bold;")
        legend_layout.addWidget(revenue_legend)
        
        # Expense legend
        expense_legend = QLabel("🔴 هزینه")
        expense_legend.setStyleSheet("color: #dc3545; font-weight: bold;")
        legend_layout.addWidget(expense_legend)
        
        # Profit legend
        profit_legend = QLabel("🔵 سود")
        profit_legend.setStyleSheet("color: #007bff; font-weight: bold;")
        legend_layout.addWidget(profit_legend)
        
        legend_layout.addStretch()
        layout.addWidget(legend_frame)
    
    def set_data(self, trend_data: List[Dict[str, Any]]):
        """Set chart data and update display with strict validation"""
        # Guard: accept only list of dicts
        safe_list = []
        if isinstance(trend_data, list):
            for it in trend_data:
                if isinstance(it, dict):
                    safe_list.append(it)
        # Keep last 12 months for a full-year view
        self.chart_data = safe_list[-12:] if len(safe_list) > 12 else safe_list
        self._update_chart()
    
    def _update_chart(self):
        """Update chart with current data"""
        if not self.chart_data:
            # Clear series and axes if empty
            self.chart.removeAllSeries()
            for ax in list(self.chart.axes()):
                self.chart.removeAxis(ax)
            return
        
        # Clear existing series and axes
        self.chart.removeAllSeries()
        for ax in list(self.chart.axes()):
            self.chart.removeAxis(ax)
        
        # Create bar sets
        revenue_set = QBarSet("درآمد")
        expense_set = QBarSet("هزینه")
        profit_set = QBarSet("سود")
        
        # Set colors
        revenue_set.setColor(Qt.green)
        expense_set.setColor(Qt.red)
        profit_set.setColor(Qt.blue)
        
        # Categories (months)
        categories = []
        
        # Add data to sets
        for item in self.chart_data:
            month = item.get("month", "")
            revenue = float(item.get("revenue", 0))
            expenses = float(item.get("expenses", 0))
            profit = float(item.get("profit", 0))
            
            # Convert month to Persian
            persian_month = self._get_persian_month(month)
            categories.append(persian_month)
            
            # Add values (convert to millions for better display)
            revenue_set.append(revenue / 1000000)
            expense_set.append(expenses / 1000000)
            profit_set.append(profit / 1000000)
        
        # Create bar series
        series = QBarSeries()
        series.append(revenue_set)
        series.append(expense_set)
        series.append(profit_set)
        
        # Add series to chart
        self.chart.addSeries(series)
        
        # Create axes
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsFont(QFont("Tahoma", 9))
        
        axis_y = QValueAxis()
        axis_y.setTitleText("مبلغ (میلیون تومان)")
        axis_y.setLabelsFont(QFont("Tahoma", 9))
        axis_y.setLabelFormat("%.1f")
        
        # Set axes
        self.chart.setAxisX(axis_x, series)
        self.chart.setAxisY(axis_y, series)
        
        # Configure chart appearance
        self.chart.legend().setVisible(False)  # We have custom legend
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # Enable value labels on bars
        series.setLabelsVisible(True)
        series.setLabelsFormat("@value")
    
    def _get_persian_month(self, month_str: str) -> str:
        """Convert month string to Persian month name"""
        try:
            if "-" in month_str:
                parts = month_str.split("-")
                if len(parts) >= 2:
                    month_num = int(parts[1])
                    return persian_month_name(month_num)
            return month_str
        except:
            return month_str