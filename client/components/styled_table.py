# -*- coding: utf-8 -*-
"""Styled table component with proper header styling"""

from PySide6.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt


class StyledTableWidget(QTableWidget):
    """QTableWidget with consistent styling and proper header display"""
    
    def __init__(self, rows=0, columns=0, parent=None):
        super().__init__(rows, columns, parent)
        self._setup_styling()
    
    def _setup_styling(self):
        """Apply consistent styling to the table"""
        # Header styling
        self.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #dee2e6;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #e9ecef;
                color: #495057;
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                font-weight: bold;
                font-size: 13px;
                text-align: center;
                min-height: 32px;
            }
            QHeaderView::section:hover {
                background-color: #dee2e6;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #f1f3f4;
                color: #212529; /* ensure visible text color */
            }
            QTableWidget::item:selected {
                background-color: #0d6efd;
                color: white;
            }
        """)
        
        # Table behavior
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setDefaultSectionSize(40)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Ensure headers are visible
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        
        # Set proper alignment for RTL
        self.setLayoutDirection(Qt.RightToLeft)