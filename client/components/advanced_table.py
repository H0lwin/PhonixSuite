# -*- coding: utf-8 -*-
"""Advanced Table Component with pagination and scrolling"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QLabel, QComboBox,
    QLineEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class AdvancedTable(QWidget):
    """Advanced table with pagination, search, and responsive design"""
    
    # Signals
    row_selected = Signal(int)  # Emitted when a row is selected
    action_clicked = Signal(str, int)  # Emitted when action button clicked (action, row)
    
    def __init__(self, headers: List[str], parent=None):
        super().__init__(parent)
        self.headers = headers
        self.all_data = []
        self.filtered_data = []
        self.current_page = 0
        self.rows_per_page = 20
        self.search_term = ""
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Search and controls bar
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(12)
        
        # Search box
        search_label = QLabel("جستجو:")
        search_label.setStyleSheet("font-weight: bold; color: #495057;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو در جدول...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0d6efd;
                outline: none;
            }
        """)
        self.search_input.textChanged.connect(self._on_search)
        
        # Rows per page selector
        rows_label = QLabel("تعداد ردیف:")
        rows_label.setStyleSheet("font-weight: bold; color: #495057;")
        self.rows_combo = QComboBox()
        self.rows_combo.addItems(["10", "20", "50", "100"])
        self.rows_combo.setCurrentText("20")
        self.rows_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                font-size: 13px;
                min-width: 60px;
            }
        """)
        self.rows_combo.currentTextChanged.connect(self._on_rows_changed)
        
        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_input, 1)
        controls_layout.addWidget(rows_label)
        controls_layout.addWidget(self.rows_combo)
        controls_layout.addStretch()
        
        layout.addWidget(controls_frame)
        
        # Table in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e9ecef;
                border-radius: 6px;
                background: white;
            }
        """)
        
        self.table = QTableWidget(0, len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                gridline-color: #e9ecef;
                font-size: 13px;
            }
            QHeaderView::section {
                background: #f8f9fa;
                padding: 8px;
                border: 1px solid #e9ecef;
                font-weight: bold;
                color: #495057;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f3f5;
            }
            QTableWidget::item:selected {
                background: #e3f2fd;
                color: #1976d2;
            }
        """)
        
        scroll_area.setWidget(self.table)
        layout.addWidget(scroll_area, 1)
        
        # Pagination controls
        pagination_frame = QFrame()
        pagination_frame.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        pagination_layout = QHBoxLayout(pagination_frame)
        pagination_layout.setSpacing(8)
        
        # Previous button
        self.prev_btn = QPushButton("◀ قبلی")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5c636a;
            }
            QPushButton:disabled {
                background: #adb5bd;
            }
        """)
        self.prev_btn.clicked.connect(self._prev_page)
        
        # Page info
        self.page_info = QLabel("صفحه 1 از 1")
        self.page_info.setAlignment(Qt.AlignCenter)
        self.page_info.setStyleSheet("font-weight: bold; color: #495057;")
        
        # Next button
        self.next_btn = QPushButton("بعدی ▶")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5c636a;
            }
            QPushButton:disabled {
                background: #adb5bd;
            }
        """)
        self.next_btn.clicked.connect(self._next_page)
        
        # Total records info
        self.total_info = QLabel("مجموع: 0 رکورد")
        self.total_info.setStyleSheet("color: #6c757d; font-size: 12px;")
        
        pagination_layout.addWidget(self.total_info)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_info)
        pagination_layout.addWidget(self.next_btn)
        
        layout.addWidget(pagination_frame)
        
        # Connect table selection
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_data(self, data: List[Dict[str, Any]]):
        """Set table data"""
        self.all_data = data
        self._apply_filter()
    
    def add_action_column(self, actions: List[str]):
        """Add action buttons column"""
        # Add action column to headers
        self.headers.append("عملیات")
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        
        # Store actions for later use under a safe name (avoid QWidget.actions method)
        self._row_actions = list(actions)
        self._has_action_column = True
    
    def _apply_filter(self):
        """Apply search filter to data"""
        if not self.search_term:
            self.filtered_data = self.all_data.copy()
        else:
            self.filtered_data = []
            for item in self.all_data:
                # Search in all string values
                found = False
                for value in item.values():
                    if isinstance(value, str) and self.search_term.lower() in value.lower():
                        found = True
                        break
                if found:
                    self.filtered_data.append(item)
        
        self.current_page = 0
        self._update_display()
    
    def _update_display(self):
        """Update table display with current page data"""
        # Calculate pagination
        total_items = len(self.filtered_data)
        total_pages = max(1, (total_items + self.rows_per_page - 1) // self.rows_per_page)
        
        # Update page info
        self.page_info.setText(f"صفحه {self.current_page + 1} از {total_pages}")
        self.total_info.setText(f"مجموع: {total_items} رکورد")
        
        # Update button states
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)
        
        # Get current page data
        start_idx = self.current_page * self.rows_per_page
        end_idx = min(start_idx + self.rows_per_page, total_items)
        page_data = self.filtered_data[start_idx:end_idx]
        
        # Clear and populate table
        self.table.setRowCount(0)
        for row_idx, item in enumerate(page_data):
            self.table.insertRow(row_idx)
            
            # Fill data columns
            col_idx = 0
            for header in self.headers[:-1] if getattr(self, '_has_action_column', False) else self.headers:
                value = str(item.get(header.lower().replace(" ", "_"), ""))
                cell_item = QTableWidgetItem(value)
                cell_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, col_idx, cell_item)
                col_idx += 1
            
            # Add action buttons if configured
            if getattr(self, '_has_action_column', False):
                self._add_action_buttons(row_idx, col_idx, start_idx + row_idx)
    
    def _add_action_buttons(self, row: int, col: int, data_index: int):
        """Add action buttons to a row"""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(4, 4, 4, 4)
        button_layout.setSpacing(4)
        
        for action in getattr(self, '_row_actions', []) or []:
            btn = QPushButton(action)
            
            # Set different colors for different actions
            if action == "حذف":
                color = "#dc3545"
                hover_color = "#c82333"
            elif action == "ویرایش":
                color = "#ffc107"
                hover_color = "#e0a800"
            else:  # نمایش and others
                color = "#28a745"
                hover_color = "#218838"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {hover_color};
                }}
            """)
            btn.clicked.connect(lambda checked, a=action, idx=data_index: self.action_clicked.emit(a, idx))
            button_layout.addWidget(btn)
        
        self.table.setCellWidget(row, col, button_widget)
    
    def _on_search(self, text: str):
        """Handle search input change"""
        self.search_term = text
        self._apply_filter()
    
    def _on_rows_changed(self, text: str):
        """Handle rows per page change"""
        self.rows_per_page = int(text)
        self.current_page = 0
        self._update_display()
    
    def _prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_display()
    
    def _next_page(self):
        """Go to next page"""
        total_pages = max(1, (len(self.filtered_data) + self.rows_per_page - 1) // self.rows_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._update_display()
    
    def _on_selection_changed(self):
        """Handle table selection change"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            # Calculate actual data index
            data_index = self.current_page * self.rows_per_page + current_row
            if data_index < len(self.filtered_data):
                self.row_selected.emit(data_index)
    
    def get_selected_data(self) -> Optional[Dict[str, Any]]:
        """Get currently selected row data"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            data_index = self.current_page * self.rows_per_page + current_row
            if data_index < len(self.filtered_data):
                return self.filtered_data[data_index]
        return None