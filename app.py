import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QMenu, QToolBar,
                             QMessageBox, QTabWidget, QPushButton, QVBoxLayout, QWidget, QInputDialog, QAction, QHBoxLayout, QLabel, QLineEdit, QToolButton, QDialog, QDialogButtonBox)
from PyQt5.QtGui import QCursor, QKeySequence, QIcon, QColor, QMovie, QBrush
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtCore import Qt, QTimer
import subprocess
import random
import string
from RunThreads import *
from mailTm import MailTM
SETTINGS_FILE = "setting/setting.json"
class SettingsManager:
    def __init__(self, file_path=SETTINGS_FILE):
        self.file_path = file_path

    def save(self, key, value):
        try:
            data = {}
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            data[key] = value

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi khi lưu cài đặt: {e}")

    def load(self, key):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get(key)
        except Exception as e:
            print(f"Lỗi khi đọc cài đặt: {e}")
        return None


        
class AccountDialog(QDialog):
    def __init__(self, parent, row, table, main_device=None):
        super().__init__(parent)
        self.adb = AdbModule()
        self.setWindowTitle("Tài khoản")
        self.row = row
        self.table = table
        self.thread = None
        self.input_fields = {}  # Sử dụng dictionary thay vì list để dễ truy cập
        self.code_input = None
        self.main_device = main_device  # ✅ sử dụng thiết bị chính
        self.mail_tm = MailTM()
        # Nếu không có thiết bị chính, dùng giá trị từ original_tab
        if not self.main_device:
            original_tab_item = self.table.item(self.row, 5)  # Cột 5 là original_tab
            if original_tab_item:
                self.main_device = original_tab_item.text()

        print("Thiết bị chính trong AccountDialog:", self.main_device)  # test

        # Khởi tạo UI components
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)
        
        self.init_ui()
        
    def init_ui(self):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # Tạo các input fields
        self.create_input_fields(container_layout)
        
        # Tạo phần mã xác nhận
        self.create_verification_code_section(container_layout)
        
        # Tạo các nút action
        self.create_action_buttons(container_layout)
        
        self.main_layout.addWidget(container)
        
        # Overlay hiển thị khi đang loading
        self.loading_overlay = LoadingOverlay(self)
        
    def create_input_fields(self, parent_layout):
        # Danh sách các trường và các thuộc tính bổ sung
        fields = [
            {"name": "username", "label": "Username", "has_button": True, "button_text": "Lấy Username"},
            {"name": "password", "label": "Password", "has_button": False},
            {"name": "mail", "label": "Mail", "has_button": True, "button_text": "Tạo Mail"},
            {"name": "tk_golike", "label": "TK Golike", "has_button": False},
            {"name": "status", "label": "Status", "has_button": False},
            {"name": "original_tab", "label": "Original Tab", "has_button": False}
        ]
        
        for idx, field in enumerate(fields):
            h_layout = QHBoxLayout()
            
            # Tạo label
            label = QLabel(field["label"])
            label.setFixedWidth(100)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Tạo input field
            input_field = QLineEdit()
            input_field.setMinimumWidth(200)
            
            # Set giá trị từ table nếu có
            item = self.table.item(self.row, idx)
            if item:
                input_field.setText(item.text())
            
            # Thêm context menu
            self.setup_context_menu(input_field)
            
            # Thêm vào layout
            h_layout.addWidget(label)
            h_layout.addWidget(input_field)
            
            # Thêm nút nếu cần
            if field["has_button"]:
                button_text = field.get("button_text", "Button")  # Sử dụng get() với giá trị mặc định
                button = QPushButton(button_text)
                
                # Gán handler tương ứng dựa vào tên trường
                if field["name"] == "username":
                    button.clicked.connect(lambda _,: self.get_user_name(self.main_device))
                elif field["name"] == "mail":
                    button.clicked.connect(lambda _,: self.create_email_account(self.input_fields["username"].text()))


                    
                h_layout.addWidget(button)

            parent_layout.addLayout(h_layout)
            
            # Lưu input field vào dictionary
            self.input_fields[field["name"]] = input_field

    def get_user_name(self, device_id):
        if not device_id:
            QMessageBox.warning(self, "Lỗi", "Device ID không hợp lệ.")
            return

        self.loading_overlay.show()
        self.thread = RunThread(task_type="username", adb_module=self.adb, device_id=device_id)
        self.thread.finished_signal.connect(self.on_username_fetched)
        self.thread.start()


    def on_username_fetched(self, username):
        self.input_fields["username"].setText(username)
        self.loading_overlay.hide()

    
    def create_verification_code_section(self, parent_layout):
        h_layout = QHBoxLayout()
        
        # Label
        label = QLabel("Mã xác nhận")
        label.setFixedWidth(100)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Input field
        self.code_input = QLineEdit()
        self.code_input.setMinimumWidth(200)
        self.setup_context_menu(self.code_input)
        
        h_layout.addWidget(label)
        h_layout.addWidget(self.code_input)
        parent_layout.addLayout(h_layout)
        
        # Nút lấy mã
        get_code_button = QPushButton("Lấy mã")
        get_code_button.clicked.connect(lambda: self.get_code(self.input_fields["mail"].text()))
        parent_layout.addWidget(get_code_button)
    
    def create_action_buttons(self, parent_layout):
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.on_accept)
        self.button_box.rejected.connect(self.reject)
        parent_layout.addWidget(self.button_box)
    
    def setup_context_menu(self, widget, field_name=None):
        """Thiết lập context menu cho widget, kèm theo tên trường (nếu cần)"""
        menu = ContextMenu(widget, self.input_fields, field_name, self.main_device)
        widget.setContextMenuPolicy(Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda pos: menu.show_menu(pos))

    def test1(self):
        print("test")
    
    def get_code(self, gmail):
        gmail = gmail
        if not gmail:
            QMessageBox.warning(self, "Lỗi", "Email không được để trống.")
            return
        
        self.loading_overlay.show()
        self.thread = RunThread(task_type="code", email=gmail)
        self.thread.finished_signal.connect(self.on_code_fetched)
        self.thread.start()
        # self.is_running = True  # ✅ THÊM DÒNG NÀY
    def on_code_fetched(self, code):
        self.code_input.setText(code)
        self.loading_overlay.hide()
    def create_email_account(self, username):
        if not username:
            QMessageBox.warning(self, "Lỗi", "Username không được để trống.")
            return

        self.loading_overlay.show()
        self.thread = RunThread(task_type="email", username=username)
        self.thread.finished_signal.connect(self.on_email_fetched)
        self.thread.start()
    def on_email_fetched(self, result):
        """
        Kết quả từ RunThread (dict): {"status": ..., "email": ..., "message": ...}
        """
        if result["status"] in ("created", "exists"):
            self.input_fields["mail"].setText(result["email"])
            self.input_fields["status"].setText(result["message"])
        else:
            self.input_fields["status"].setText(result["message"])

        self.loading_overlay.hide()


                

    
    def on_accept(self):
        # Lấy thứ tự của các trường để ghi vào table
        field_order = ["username", "password", "mail", "tk_golike", "status", "original_tab"]
        
        for col, field_name in enumerate(field_order):
            new_text = self.input_fields[field_name].text()
            self.table.setItem(self.row, col, QTableWidgetItem(new_text))
        
        self.accept()


class ContextMenu:
    """Class quản lý context menu cho các widget"""
    def __init__(self, widget, input_fields=None, field_name=None, main_device=None):
        self.widget = widget
        self.input_fields = input_fields
        self.field_name = field_name
        self.main_device = main_device
        self.adb = AdbModule()
    def show_menu(self, pos):
        menu = QMenu()

        # Thêm các action thông dụng
        paste_action = menu.addAction("Paste")
        paste_action.triggered.connect(self.paste)

        menu.addSeparator()

        menu.exec_(self.widget.mapToGlobal(pos))

    def paste(self):
        if isinstance(self.widget, QLineEdit):
            device_id = self.main_device
            text_input = self.widget.text()  # Lấy text hiện tại từ widget
            print("Device", device_id)
            print("Paste triggered - Current field value:", text_input)
            self.adb.paste_text_to_device(text_input, device_id)
class ContextMenuManager:
    def __init__(self, parent, table_getter_func, create_action_func, excel_table=None):
        """
        :param parent: QWidget cha (self)
        :param table_getter_func: Hàm lấy bảng từ pos nếu không truyền (self.sender hoặc truyền vào)
        :param create_action_func: Hàm tạo QAction có tooltip (self.create_menu_action)
        :param excel_table: Nếu muốn xử lý chuyển tab
        """
        self.parent = parent
        self.get_table = table_getter_func
        self.create_action = create_action_func
        self.excel_table = excel_table

    def show_warehouse_menu(self, pos, table=None):
        table = table or self.get_table()
        row = table.rowAt(pos.y())
        if row != -1:
            table.selectRow(row)

        menu = QMenu(self.parent)

        # Thêm hàng
        add_row_action = self.create_action(menu, "Thêm hàng", "Thêm một hàng mới vào bảng")
        add_row_action.triggered.connect(lambda: self.parent.add_row(table))
        menu.addAction(add_row_action)

        selected_items = table.selectedItems()
        selected_rows = set(item.row() for item in selected_items)

        if len(selected_rows) == 1:
            menu.addSeparator()

            # Submenu "Chức năng"
            function_menu = QMenu("Chức năng", menu)
            function_menu.setToolTipsVisible(True)
            function_menu.setStyleSheet(menu.styleSheet())

            create_account_action = self.create_action(function_menu, "Tạo tài khoản", "Hiển thị thông tin tài khoản đang chọn")
            create_account_action.triggered.connect(lambda: self.parent.open_account_dialog(selected_rows, table))
            function_menu.addAction(create_account_action)

            menu.addMenu(function_menu)

            delete_action = self.create_action(menu, "Xóa tài khoản", "Xóa hàng được chọn")
            delete_action.triggered.connect(lambda: self.parent.delete_multiple_accounts(selected_rows, table))
            menu.addAction(delete_action)

            if self.excel_table:
                transfer_to_tab_action = self.create_action(menu, "Chuyển sang Tab", "Chuyển hàng sang Tab khác")
                transfer_to_tab_action.triggered.connect(self.parent.transfer_selected_to_tab)
                menu.addAction(transfer_to_tab_action)

        elif len(selected_rows) > 1:
            menu.addSeparator()
            delete_action = self.create_action(menu, f"Xóa {len(selected_rows)} tài khoản", f"Xóa {len(selected_rows)} hàng được chọn")
            delete_action.triggered.connect(lambda: self.parent.delete_multiple_accounts(selected_rows, table))
            menu.addAction(delete_action)

            if self.excel_table:
                transfer_to_tab_action = self.create_action(menu, f"Chuyển {len(selected_rows)} sang Tab", f"Chuyển {len(selected_rows)} hàng sang Tab khác")
                transfer_to_tab_action.triggered.connect(self.parent.transfer_selected_to_tab)
                menu.addAction(transfer_to_tab_action)

        menu.exec_(QCursor.pos())

    def show_excel_menu(self, pos, table):
        row = table.rowAt(pos.y())
        menu = QMenu(self.parent)

        # Hành động chung
        global_action = self.create_action(menu, "Thêm hàng", "Thêm hàng mới vào bảng này")
        menu.addAction(global_action)

        menu.addSeparator()

        if row >= 0:
            table.selectRow(row)
            row_data = self.parent.get_row_data(table, row)

            function_menu = QMenu("Chức năng", menu)
            function_menu.setStyleSheet(menu.styleSheet())

            login_action = self.create_action(function_menu, "Login bằng mail", f"Đăng nhập cho: {row_data.get('username', 'N/A')}")
            send_verify_code_action = self.create_action(function_menu, "Gửi mã xác nhận", f"Gửi mã xác nhận cho: {row_data.get('gmail', 'N/A')}")
            
            function_menu.addAction(login_action)
            function_menu.addAction(send_verify_code_action)
            
            menu.addMenu(function_menu)

            transfer_action = self.create_action(menu, "Chuyển vào Kho", "Chuyển hàng đã chọn sang Kho")
            delete_action = self.create_action(menu, "Xóa hàng", "Xóa hàng đã chọn")

            menu.addAction(transfer_action)
            menu.addAction(delete_action)

        action = menu.exec_(QCursor.pos())

        if action == global_action:
            self.parent.add_row(table)
        elif row >= 0:
            if action == login_action:
                print(f"Đăng nhập bằng mail cho hàng: {row_data}")
            elif action == send_verify_code_action:
                
                gmail = row_data.get('Mail', 'N/A')
                print(f"Gmail được lấy từ row_data: {gmail}")
                self.get_code(gmail)

            elif action == transfer_action:
                self.parent.transfer_row_to_warehouse(table, row)
            elif action == delete_action:
                self.parent.delete_selected_rows(table)
    def get_code(self, gmail):
        gmail = gmail
        if not gmail:
            QMessageBox.warning(self, "Lỗi", "Email không được để trống.")
            return
        
        self.loading_overlay.show()
        self.thread = RunThread(task_type="code", email=gmail)
        self.thread.finished_signal.connect(self.on_code_fetched)
        self.thread.start()
        # self.is_running = True  # ✅ THÊM DÒNG NÀY
    def on_code_fetched(self, code):
        self.code_input.setText(code)
        self.loading_overlay.hide()
class CustomTableWidget(QTableWidget):
    def __init__(self, row_count=0, column_count=6, parent=None, context_menu_callback=None, item_changed_callback=None):
        super().__init__(row_count, column_count, parent)

        self.setHorizontalHeaderLabels(["Username", "Password", "Mail", "TK Golike", "Status", "Original Tab"])
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        if context_menu_callback:
            self.customContextMenuRequested.connect(lambda pos: context_menu_callback(pos, self))

        if item_changed_callback:
            self.itemChanged.connect(item_changed_callback)

        self.verticalHeader().setDefaultSectionSize(40)
        self.setEditTriggers(QTableWidget.DoubleClicked)

    def populate_with_accounts(self, accounts):
        self.setRowCount(len(accounts))
        for row_idx, account in enumerate(accounts):
            self.setItem(row_idx, 0, QTableWidgetItem(account.get('username', '')))
            self.setItem(row_idx, 1, QTableWidgetItem(account.get('password', '')))
            self.setItem(row_idx, 2, QTableWidgetItem(account.get('email', '')))
            self.setItem(row_idx, 3, QTableWidgetItem(account.get('linked_golike', '')))
            self.setItem(row_idx, 4, QTableWidgetItem(account.get('status', '')))
            self.setItem(row_idx, 5, QTableWidgetItem(account.get('original_tab', '')))
class LoadingOverlay:
    """
    Class quản lý loading overlay cho bất kỳ widget nào trong ứng dụng Qt.
    Hiển thị một animation loading gif trên toàn bộ widget cha.
    """
    def __init__(self, parent_widget, gif_path="themes/loadding_small.gif"):
        """
        Khởi tạo overlay loading
        
        Args:
            parent_widget: Widget cha sẽ chứa overlay
            gif_path: Đường dẫn đến file gif loading animation
        """
        self.parent = parent_widget
        
        # Tạo overlay label
        self.overlay = QLabel(parent_widget)
        self.overlay.setAlignment(Qt.AlignCenter)
        
        # Tạo và thiết lập loading movie
        self.loading_movie = QMovie(gif_path)
        self.overlay.setMovie(self.loading_movie)
        self.overlay.setVisible(False)
        
        # Lưu resize event gốc của parent
        self.original_resize_event = parent_widget.resizeEvent
        
        # Override resize event để cập nhật kích thước overlay
        def new_resize_event(event):
            self.update_size()
            if self.original_resize_event:
                self.original_resize_event(event)
        
        parent_widget.resizeEvent = new_resize_event
        
        # Cập nhật kích thước ban đầu
        self.update_size()
    
    def update_size(self):
        """Cập nhật kích thước overlay theo kích thước parent"""
        self.overlay.setGeometry(0, 0, self.parent.width(), self.parent.height())
    
    def show(self):
        """Hiển thị overlay và bắt đầu animation"""
        self.overlay.setVisible(True)
        self.overlay.raise_()  # Đảm bảo overlay ở trên cùng
        self.loading_movie.start()

        
    def hide(self):
        """Ẩn overlay và dừng animation"""
        self.loading_movie.stop()
        self.overlay.setVisible(False)
        
    def is_visible(self):
        """Kiểm tra xem overlay có đang hiển thị không"""
        return self.overlay.isVisible()

class HoverMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Stylesheet for hover and general menu styling
        self.setStyleSheet("""
        QMenu {
            # background-color: white;
            border: 1px solid #D3D3D3;
            padding: 5px;
            border-radius: 5px;
        }
        QMenu::item {
            padding: 5px 20px;
            background-color: transparent;
            color: black;
        }
        QMenu::item:selected {
            background-color: #E0E0E0;
            color: black;
        }
        QMenu::item:disabled {
            color: #888888;
        }
        """)
class BaseAccountTableManager:
    def __init__(self):
        self.adb = AdbModule()
        self.settings = SettingsManager()

        self.device_id = self.adb.get_connected_devices()
        self.device_index = self.load_device_index()  # Tải chỉ số thiết bị đã gán từ file

        # Các âm tiết thường gặp trong họ, tên đệm, và tên
        self.am_tiet_ho = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Hồ", "Đinh", "Tô"]
        self.am_tiet_dem = ["Văn", "Hữu", "Minh", "Thị", "Thanh", "Thành", "Ngọc", "Gia", "Hải", "Nhật", "Quốc", "Bảo", "Chí", "Tường"]
        self.am_tiet_ten = ["Anh", "Bình", "Cường", "Dũng", "Hạnh", "Hùng", "Linh", "My", "Nam", "Phương", "Quỳnh", "Tú", "Lam", "Như", "Thy"]


    
    """Base class for account table management with common methods"""

    def mark_unsaved(self):
        """Mark the data as unsaved"""
        if not hasattr(self, 'data_changed'):
            self.data_changed = False
        
        if not self.data_changed:
            # Modify window title to indicate unsaved changes
            current_title = self.windowTitle()
            if not current_title.endswith('*'):
                self.setWindowTitle(f"{current_title} *")
            self.data_changed = True

    def get_row_data(self, table, row):
        """Get row data as a dictionary"""
        if row < 0:
            return {}

        row_data = {
            table.horizontalHeaderItem(col).text(): table.item(row, col).text() if table.item(row, col) else ""
            for col in range(table.columnCount())
        }
        return row_data

    def check_user_exists(self, username):
        """Kiểm tra xem user đã tồn tại trong data.json hoặc warehouse.json chưa"""
        filenames = ["data/data.json", "data/warehouse.json"]

        for filename in filenames:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Kiểm tra trong file data.json có cấu trúc tabs
                    if "tabs" in data:
                        for tab in data["tabs"]:
                            for account in tab.get("accounts", []):
                                if str(account.get("username")).strip().lower() == str(username).strip().lower():
                                    return True
                    
                    # Kiểm tra trong file warehouse.json có cấu trúc accounts
                    if "accounts" in data:
                        for account in data["accounts"]:
                            if str(account.get("username")).strip().lower() == str(username).strip().lower():
                                return True

            except (FileNotFoundError, json.JSONDecodeError):
                continue  # Bỏ qua nếu file không tồn tại hoặc bị lỗi JSON

        return False

    def add_row(self, table):
        """Thêm một dòng mới vào bảng, yêu cầu nhập user trước"""

        # Giới hạn chỉ áp dụng cho ExcelLikeTable (data/data.json)
        if isinstance(self, ExcelLikeTable) and table.rowCount() >= 8:
            QMessageBox.warning(self, "Cảnh báo", "Bảng này đã đủ 8 dòng, không thể thêm dòng mới.")
            return

        while True:
            user, ok = QInputDialog.getText(self, "Nhập User", "Nhập tên user:")
            
            if not ok:
                return

            if not user.strip():
                QMessageBox.warning(self, "Cảnh báo", "Không nhập user, hủy thêm dòng mới.")
                return

            if self.check_user_exists(user.strip()):
                QMessageBox.warning(self, "Cảnh báo", f"User '{user.strip()}' đã tồn tại trong hệ thống!")
            else:
                break

        row_count = table.rowCount()
        table.insertRow(row_count)

        # Điền user vào cột đầu tiên
        table.setItem(row_count, 0, QTableWidgetItem(user.strip()))

        # Điền các cột còn lại rỗng
        for col in range(1, table.columnCount()):
            table.setItem(row_count, col, QTableWidgetItem(""))

        self.mark_unsaved()
        
        try:
            if hasattr(self, 'table'):
                self.save_to_json("data/warehouse.json")
            
            if hasattr(self, 'tabs'):
                self.save_to_json("data/data.json")
        except Exception as e:
            print(f"Lỗi khi lưu dữ liệu: {e}")
            QMessageBox.warning(self, "Lỗi", f"Không thể lưu dữ liệu: {e}")

    def delete_selected_rows(self, table):
        """
        Delete selected rows from the table
        
        :param table: QTableWidget from which rows will be deleted
        """
        # Get selected rows
        selected_rows = set(item.row() for item in table.selectedItems())
        
        # Confirm deletion if rows are selected
        if selected_rows:
            reply = QMessageBox.question(
                self, 
                "Xác nhận xóa", 
                f"Bạn có chắc chắn muốn xóa {len(selected_rows)} dòng đã chọn?", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Sort rows in reverse to avoid index shifting issues
                for row in sorted(selected_rows, reverse=True):
                    table.removeRow(row)
                
                # Mark as unsaved
                self.mark_unsaved()
    def create_menu_action(self, menu, text, tooltip, icon_path=None, enabled=True):
        """
        Create a menu action with hover tooltip and optional icon
        
        :param menu: Parent menu
        :param text: Action text
        :param tooltip: Tooltip text to show on hover
        :param icon_path: Optional path to icon
        :param enabled: Whether the action is enabled
        :return: QAction
        """
        action = QAction(text, menu)
        action.setToolTip(tooltip)
        
        # Set icon if path is provided
        if icon_path:
            action.setIcon(QIcon(icon_path))
        
        # Set enabled/disabled state
        action.setEnabled(enabled)
        
        return action

    def save_to_json(self, filename=None):
        """
        Save data to JSON with context-specific filename
        If no filename is provided, use a default based on the interface
        """
        # Default filename selection if not provided
        if filename is None:
            if hasattr(self, 'table'):
                filename = "data/warehouse.json"
            elif hasattr(self, 'tabs'):
                filename = "data/data.json"
            else:
                raise ValueError("Cannot determine save file")

        # Check if data has changed
        if not hasattr(self, 'data_changed') or not self.data_changed:
            return

        # Determine the table to save from
        if hasattr(self, 'table'):
            table = self.table
            data = {"accounts": []}
            
            for row in range(table.rowCount()):
                account = {
                    "username": "",
                    "password": "",
                    "email": "",
                    "linked_golike": "",
                    "status": "",
                    "original_tab": ""
                }
                
                # Map table columns to account keys
                column_mapping = {
                    "Username": "username",
                    "Password": "password",
                    "Mail": "email",
                    "TK Golike": "linked_golike",
                    "Status": "status",
                    "Original Tab": "original_tab"
                }
                
                for col in range(table.columnCount()):
                    header = table.horizontalHeaderItem(col).text()
                    if header in column_mapping:
                        key = column_mapping[header]
                        account[key] = table.item(row, col).text() if table.item(row, col) else ""
                
                data["accounts"].append(account)
        
        elif hasattr(self, 'tabs'):
            data = {"tabs": []}

            for index in range(self.tabs.count()):
                tab_name = self.tabs.tabText(index)
                tab = self.tabs.widget(index)
                table = tab.layout().itemAt(0).widget()

                accounts = []
                for row in range(table.rowCount()):
                    account = {
                        "username": table.item(row, 0).text() if table.item(row, 0) else "",
                        "password": table.item(row, 1).text() if table.item(row, 1) else "",
                        "email": table.item(row, 2).text() if table.item(row, 2) else "",
                        "linked_golike": table.item(row, 3).text() if table.item(row, 3) else "",
                        "status": table.item(row, 4).text() if table.item(row, 4) else "",
                        "original_tab": table.item(row, 5).text() if table.item(row, 5) else ""
                    }
                    accounts.append(account)

                data["tabs"].append({
                    "name": tab_name,
                    "accounts": accounts
                })
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Reset changed status
        if hasattr(self, 'table'):
            self.setWindowTitle("Kho Tài Khoản")
        elif hasattr(self, 'tabs'):
            self.setWindowTitle("Excel-like Table with Context Menu")
        
        self.data_changed = False
        # print(f"Data saved successfully to {filename}")

    def load_from_json(self, filename="data/data.json"):
        """Load data from JSON, supporting both single table and tab-based structures"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if data contains multiple tabs or a single table
            if "tabs" in data:
                # Load data into multiple tabs
                for tab_data in data["tabs"]:
                    tab_name = tab_data.get("name", "Unnamed Tab")
                    accounts = tab_data.get("accounts", [])
                    self.create_new_tab_with_data(tab_name, accounts)
            elif "accounts" in data:
                # Load data into a single table
                table = self.table if hasattr(self, 'table') else self.tabs.currentWidget().layout().itemAt(0).widget()
                table.setRowCount(0)  # Clear existing rows

                for account in data["accounts"]:
                    row_count = table.rowCount()
                    table.insertRow(row_count)

                    for col, (header, value) in enumerate(account.items()):
                        table.setItem(row_count, col, QTableWidgetItem(str(value)))

            # Reset change status
            self.data_changed = False
            print("Data loaded from JSON")
        
        except FileNotFoundError:
            print("No saved data found.")
        except json.JSONDecodeError:
            print("Error loading JSON data.")

    def closeEvent(self, event):
        """Handle window closing with unsaved changes"""
        if hasattr(self, 'data_changed') and self.data_changed:
            reply = QMessageBox.question(self, "Unsaved Changes", 
                                         "Bạn có muốn lưu thay đổi trước khi đóng?", 
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, 
                                         QMessageBox.Save)
            
            if reply == QMessageBox.Save:
                self.save_to_json()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
            

        
    def delete_account(self, row, table=None):
        """
        Delete a specific row from the table.
        If no table is provided, try to use self.table or the current tab's table.
        """
        # If no table is provided, try to find one
        if table is None:
            if hasattr(self, 'table'):
                table = self.table
            elif hasattr(self, 'tabs'):
                # For multi-tab interfaces, use the current tab's table
                current_tab = self.tabs.currentWidget()
                table = current_tab.layout().itemAt(0).widget()
            else:
                raise ValueError("No table found to delete row")

        if row < 0 or row >= table.rowCount():
            return

        # Remove row from table
        table.removeRow(row)
        
        # Mark as unsaved
        self.mark_unsaved()

        # Optional: Save changes (can be overridden in specific implementations)
        try:
            self.save_to_json()
        except Exception:
            # If save fails, it's not critical
            pass

    
    def load_device_index(self):
        try:
            with open('setting/device_index.json', 'r') as file:
                data = json.load(file)
                return data.get('device_index', 0)  # Mặc định là 0 nếu không tìm thấy chỉ số
        except FileNotFoundError:
            return 0  # Nếu file không tồn tại, bắt đầu từ thiết bị đầu tiên

    def save_device_index(self):
        with open('setting/device_index.json', 'w') as file:
            json.dump({'device_index': self.device_index}, file)

    def tao_ten_ngau_nhien(self):
        ho = random.choice(self.am_tiet_ho)  # Chọn họ ngẫu nhiên
        ten_dem = random.choice(self.am_tiet_dem) if random.random() > 0.3 else ""  # Tên đệm có thể có hoặc không
        ten = random.choice(self.am_tiet_ten)  # Chọn tên ngẫu nhiên

        # Kết hợp họ, tên đệm và tên sao cho không có khoảng trắng thừa
        if ten_dem:  # Nếu có tên đệm
            result_name = f"{ho} {ten_dem} {ten}"
        else:  # Nếu không có tên đệm
            result_name = f"{ho} {ten}"

        # Loại bỏ khoảng trắng thừa ở đầu và cuối tên
        result_name = result_name.strip()

        # In ra tên vừa tạo

        # Thêm dòng mới vào bảng
        row_position = self.table.rowCount()  # Lấy số dòng hiện tại
        self.table.insertRow(row_position)  # Thêm dòng mới vào bảng

        # Gán tên ngẫu nhiên vào cột "Username" (cột đầu tiên)
        self.table.setItem(row_position, 0, QTableWidgetItem(result_name))

        # Gán thiết bị vào cột số 6 (Cột thiết bị)
        device = self.device_id[self.device_index]
        self.table.setItem(row_position, 5, QTableWidgetItem(device))  # Cột số 6 là cột 5 (chỉ số bắt đầu từ 0)

        # Cập nhật chỉ số thiết bị tiếp theo
        self.device_index += 1

        # Nếu đã gán hết tất cả thiết bị, quay lại từ đầu
        if self.device_index >= len(self.device_id):
            self.device_index = 0

        # Lưu chỉ số thiết bị sau khi gán
        self.save_device_index()

        # Gán các cột khác nếu cần
        self.table.setItem(row_position, 1, QTableWidgetItem("Nguyen2004nam@"))
        # self.table.setItem(row_position, 2, QTableWidgetItem("email"))
        # ...

        return result_name


class WarehouseWindow(QMainWindow, BaseAccountTableManager):
    def __init__(self, parent=None, excel_table=None):
        super().__init__(parent)  # Pass parent to the superclass

        self.excel_table = excel_table
                # Lấy danh sách thiết bị từ ADB
        from adbutils import adb  # nếu bạn dùng adbutils
        devices = adb.device_list()
        self.saved_main_device = self.settings.load("main_device")
        self.context_menu = ContextMenuManager(
            self,
            table_getter_func=lambda: self.sender(),
            create_action_func=self.create_menu_action,
            excel_table=self.excel_table
        )
        # Store reference to excel table
        
        self.setWindowTitle("Kho Tài Khoản")
        
        # Modify geometry to position next to the Excel-like table
        if excel_table:
            excel_geometry = excel_table.geometry()
            self.setGeometry(
                excel_geometry.x() + excel_geometry.width(), 
                excel_geometry.y(), 
                800, 
                600
            )
        else:
            self.setGeometry(200, 200, 800, 600)

        # Track changes
        self.data_changed = False

        # Create toolbar
        self.toolbar = QToolBar("Thanh công cụ")
        self.addToolBar(self.toolbar)

        # Add row button
        self.add_row_button = QPushButton("Thêm hàng")
        self.add_row_button.clicked.connect(self.tao_ten_ngau_nhien)  # Connect to method directly
        self.toolbar.addWidget(self.add_row_button)
# Sau đoạn self.theme_button...
        self.main_device_menu = QMenu("Chọn thiết bị chính", self)
        self.main_device_actions = {}
        self.current_main_device_action = None


        for dev in devices:
            device_id = dev.serial
            action = QAction(device_id, self)
            action.setCheckable(True)
            if device_id == self.saved_main_device:
                action.setChecked(True)
                self.current_main_device_action = action
            action.triggered.connect(lambda checked, dev_id=device_id, act=action: self.set_main_device(dev_id, act))
            self.main_device_menu.addAction(action)
            self.main_device_actions[device_id] = action

        self.device_button = QToolButton()
        self.device_button.setText("📱 Thiết bị chính")
        self.device_button.setMenu(self.main_device_menu)
        self.device_button.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(self.device_button)
        # Nếu đã có thiết bị chính thì thay đổi text hiển thị
        if self.saved_main_device:
            self.device_button.setText(f"📱 {self.saved_main_device}")
        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Create table using a separate method
        self.create_table()
        self.load_main_device_menu()

        layout.addWidget(self.table)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Save shortcut
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_to_json)
            
    def set_main_device(self, device_id, action):
        if self.current_main_device_action:
            self.current_main_device_action.setChecked(False)
        action.setChecked(True)
        self.current_main_device_action = action

        # Lưu thiết bị chính (có thể là None)
        self.settings.save("main_device", device_id)

        # Cập nhật văn bản hiển thị trên nút
        if device_id:
            self.device_button.setText(f"📱 {device_id}")
        else:
            self.device_button.setText("📱 Không chọn")

        self.load_main_device_menu()  # 🔁 Cập nhật lại menu

    def load_main_device_menu(self):
        from adbutils import adb
        devices = adb.device_list()
        self.saved_main_device = self.settings.load("main_device")
        self.main_device_menu = QMenu("Chọn thiết bị chính", self)
        self.main_device_actions = {}
        self.current_main_device_action = None

        # Tùy chọn "Không chọn thiết bị"
        none_action = QAction("❌ None", self)
        none_action.setCheckable(True)
        if self.saved_main_device is None:
            none_action.setChecked(True)
            self.current_main_device_action = none_action
        none_action.triggered.connect(lambda checked, dev_id=None, act=none_action: self.set_main_device(dev_id, act))
        self.main_device_menu.addAction(none_action)
        self.main_device_actions[None] = none_action

        # Thêm các thiết bị thực tế
        for dev in devices:
            device_id = dev.serial
            action = QAction(device_id, self)
            action.setCheckable(True)
            if device_id == self.saved_main_device:
                action.setChecked(True)
                self.current_main_device_action = action
            action.triggered.connect(lambda checked, dev_id=device_id, act=action: self.set_main_device(dev_id, act))
            self.main_device_menu.addAction(action)
            self.main_device_actions[device_id] = action

        # Cập nhật menu trong giao diện
        if hasattr(self, "device_button"):
            self.device_button.setMenu(self.main_device_menu)
            if self.saved_main_device:
                self.device_button.setText(f"📱 {self.saved_main_device}")
            else:
                self.device_button.setText("📱 Không chọn")
        else:
            self.device_button = QToolButton()
            self.device_button.setText("📱 Thiết bị chính")
            self.device_button.setMenu(self.main_device_menu)
            self.device_button.setPopupMode(QToolButton.InstantPopup)
            self.toolbar.addWidget(self.device_button)


    def create_table(self):
        self.table = CustomTableWidget(
            context_menu_callback=self.context_menu.show_warehouse_menu,
            item_changed_callback=self.mark_unsaved
)

        self.load_from_json("data/warehouse.json")



    def transfer_selected_to_tab(self):
        """Transfer selected rows from warehouse to a tab based on column 6 value"""
        if not self.excel_table:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy cửa sổ Excel-like.")
            return

        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn hàng để chuyển.")
            return

        selected_rows = set(item.row() for item in selected_items)
        tab_names = {self.excel_table.tabs.tabText(i): i for i in range(self.excel_table.tabs.count())}

        last_successful_tab_index = None

        for row in sorted(selected_rows, reverse=True):
            column_6_item = self.table.item(row, 5)
            if not column_6_item:
                QMessageBox.warning(self, "Lỗi", f"Hàng {row + 1} không có dữ liệu cột 6.")
                continue

            tab_name = column_6_item.text().strip()
            if tab_name not in tab_names:
                QMessageBox.warning(self, "Lỗi", f"Không tìm thấy tab '{tab_name}' cho hàng {row + 1}.")
                continue

            destination_tab_index = tab_names[tab_name]
            destination_tab = self.excel_table.tabs.widget(destination_tab_index)
            destination_table = destination_tab.layout().itemAt(0).widget()

            # Kiểm tra nếu tab đã đủ 8 dòng
            if destination_table.rowCount() >= 8:
                QMessageBox.warning(self, "Thông báo", f"Tab '{tab_name}' đã đủ 8 dòng. Không thể thêm hàng {row + 1}.")
                continue

            # Sao chép dữ liệu hàng
            row_data = [
                self.table.item(row, col).text() if self.table.item(row, col) else ""
                for col in range(self.table.columnCount())
            ]

            # Chèn hàng vào bảng đích
            destination_table.insertRow(destination_table.rowCount())
            for col, value in enumerate(row_data):
                destination_table.setItem(
                    destination_table.rowCount() - 1, 
                    col, 
                    QTableWidgetItem(value)
                )

            # Xóa hàng khỏi bảng nguồn
            self.table.removeRow(row)

            last_successful_tab_index = destination_tab_index  # cập nhật nếu thành công

            # Scroll tới dòng mới được thêm vào
            if destination_table.rowCount() > 0:
                last_row_index = destination_table.rowCount() - 1
                destination_table.scrollToItem(destination_table.item(last_row_index, 0), QTableWidget.PositionAtCenter)
                destination_table.setCurrentCell(last_row_index, 0)

        # Chuyển đến tab mới nếu có hàng nào được chuyển
        if last_successful_tab_index is not None:
            self.excel_table.tabs.setCurrentIndex(last_successful_tab_index)

        # Đánh dấu dữ liệu chưa được lưu
        self.mark_unsaved()
        self.excel_table.mark_unsaved()

        try:
            self.save_to_json()
            self.excel_table.save_to_json()
        except Exception as e:
            print(f"Error saving data: {e}")




    def open_account_dialog(self, selected_rows, table):
        if not selected_rows:
            return
        row = list(selected_rows)[0]
        dialog = AccountDialog(self, row, table, main_device=self.saved_main_device)
        dialog.exec_()

    def delete_multiple_accounts(self, rows, table):
        """
        Delete multiple selected rows from the table.
        
        :param rows: Set of row indices to delete
        :param table: The table widget
        """
        # Sort rows in reverse to avoid index shifting issues
        for row in sorted(rows, reverse=True):
            table.removeRow(row)
        
        # Mark as unsaved
        self.mark_unsaved()
    def closeEvent(self, event):
        """
        Ghi đè phương thức closeEvent để đảm bảo lưu dữ liệu
        và giữ nguyên logic đóng cửa sổ
        """
        # Kiểm tra và lưu dữ liệu nếu có thay đổi
        if hasattr(self, 'data_changed') and self.data_changed:
            # Thử lưu dữ liệu của cả warehouse và excel-like table
            try:
                self.save_to_json()
                if self.excel_table:
                    self.excel_table.save_to_json()
            except Exception as e:
                print(f"Lỗi khi lưu dữ liệu: {e}")
        # Remove reference from excel_table if it exists
        if self.excel_table and hasattr(self.excel_table, 'warehouse_window'):
            self.excel_table.warehouse_window = None
        # Gọi phương thức closeEvent của lớp cha để đảm bảo đóng cửa sổ đúng
        super().closeEvent(event)
        
    def add_row_with_data(self, row_data):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        for col, data in enumerate(row_data):
            self.table.setItem(row_count, col, QTableWidgetItem(data))

class ExcelLikeTable(QMainWindow, BaseAccountTableManager):
    def __init__(self):
        super().__init__()
        self.runner = None
        self.is_running = False

        self.context_menu = ContextMenuManager(
            self,
            table_getter_func=lambda: self.sender(),  # không thực sự dùng ở đây
            create_action_func=self.create_menu_action
        )
        self.current_theme_action = None  # ✅ Biến để lưu theme hiện tại
        self.setWindowTitle("Excel-like Table with Context Menu")
        self.setGeometry(0, 0, 1000, 800)
        self.warehouse_window = None

        # Menu bar
        self.menu_bar = self.menuBar()

        # Toolbar
        self.toolbar = QToolBar("Thanh công cụ")
        self.addToolBar(self.toolbar)

        # Thêm nút
        self.add_table_button = QPushButton("Thêm bảng")
        self.add_table_button.clicked.connect(self.create_new_tab)
        self.toolbar.addWidget(self.add_table_button)

        self.warehouse_button = QPushButton("Kho")
        self.warehouse_button.clicked.connect(self.open_warehouse)
        self.toolbar.addWidget(self.warehouse_button)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_process)
        self.toolbar.addWidget(self.start_button)

        # Tạo menu giao diện và gắn vào ToolButton
        saved_theme_name = self.settings.load("theme")  # ✅ Lưu theo tên theme
        self.theme_menu = QMenu("Chọn giao diện", self)
        self.themes = {
            "Defaul": "themes/defaul.qss",
            "Dark": "themes/defaul Dark.qss",
            "Ice Crystal": "themes/Ice Crystal.qss",
            "Vintage Coffee": "themes/Vintage Coffee.qss",
            "Soft Pastel": "themes/Soft Pastel.qss",
        }
        self.theme_actions = {}  # Dictionary lưu QAction tương ứng

        for theme_name, file_path in self.themes.items():
            action = QAction(theme_name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, path=file_path, act=action: self.load_stylesheet(path, act))
            self.theme_menu.addAction(action)
            self.theme_actions[file_path] = action

        # ToolButton để hiện menu
        self.theme_button = QToolButton()
        self.theme_button.setText("🎨 " + (saved_theme_name if saved_theme_name else "Giao diện"))
        self.theme_button.setMenu(self.theme_menu)
        self.theme_button.setPopupMode(QToolButton.InstantPopup)
        self.toolbar.addWidget(self.theme_button)
        if saved_theme_name:
            self.theme_button.setText("🎨 " + saved_theme_name)


        # Separator
        self.toolbar.addSeparator()

        # Tìm kiếm
        self.add_search_bar()

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.tabs)

        self.container = QWidget()
        self.container.setLayout(self.main_layout)
        self.setCentralWidget(self.container)

        # Phím tắt
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_to_json)

        self.data_changed = False

        # Load dữ liệu ban đầu
        self.load_from_json("data/data.json")
        # ✅ Load theme đã lưu hoặc mặc định
        if saved_theme_name and saved_theme_name in self.themes:
            saved_theme_path = self.themes[saved_theme_name]
            self.load_stylesheet(saved_theme_path, self.theme_actions[saved_theme_path])
        else:
            default_theme_name = "Defaul"
            default_theme_path = self.themes[default_theme_name]
            self.load_stylesheet(default_theme_path, self.theme_actions[default_theme_path])

    def start_process(self):
        if not self.is_running:
            # Start process
            adb = AdbModule()
            connected_devices = adb.get_connected_devices()

            if not connected_devices:
                print("Không có thiết bị nào được kết nối!")
                return

            self.runner = MultiDeviceRunner(devices=connected_devices)
            self.runner.run_in_background()

            self.start_button.setText("Stop")
            self.is_running = True
        else:
            # Stop process
            if self.runner:
                self.runner.stop()
                print("Đã dừng tiến trình MultiDeviceRunner.")
            self.start_button.setText("Start")
            self.is_running = False

            
    def load_stylesheet(self, path, action):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

            # Bỏ chọn action cũ
            if self.current_theme_action:
                self.current_theme_action.setChecked(False)

            # Chọn action hiện tại
            action.setChecked(True)
            self.current_theme_action = action

            # ✅ Lưu tên theme thay vì path
            for name, filepath in self.themes.items():
                if filepath == path:
                    self.settings.save("theme", name)
                    self.theme_button.setText(f"🎨 {name}")
                    break

        except Exception as e:
            print(f"Lỗi khi load QSS từ {path}: {e}")



    def add_search_bar(self):
        """Add a search bar to the toolbar"""
        # Create a layout for search bar components
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(5, 0, 5, 0)

        # Create search label
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        # Create search input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter text to search...")
        search_layout.addWidget(self.search_input)

        # Create a widget to hold the search layout
        search_widget = QWidget()
        search_widget.setLayout(search_layout)

        # Add widget to toolbar
        self.toolbar.addWidget(search_widget)

        # Timer for delayed search
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)  # Chỉ chạy một lần sau khi dừng nhập
        self.search_timer.timeout.connect(self.search_tables)

        # Kết nối QLineEdit với QTimer để trì hoãn tìm kiếm
        self.search_input.textChanged.connect(self.start_search_timer)

        # Kết nối sự kiện Enter để tìm kiếm ngay lập tức
        self.search_input.returnPressed.connect(self.search_tables)

    def start_search_timer(self):
        """Start the search timer when user types"""
        self.search_timer.start(500)  # Chờ 500ms trước khi thực hiện tìm kiếm

    def search_tables(self):
        """Tìm kiếm theo cột đầu tiên và cả tên tab"""
        search_text = self.search_input.text().strip().lower()

        # Nếu ô tìm kiếm trống, hiển thị lại tất cả các hàng
        if not search_text:
            for tab_index in range(self.tabs.count()):
                tab = self.tabs.widget(tab_index)
                table = tab.layout().itemAt(0).widget()
                for row in range(table.rowCount()):
                    table.setRowHidden(row, False)
                    # Khôi phục màu nền của tất cả các ô khi không tìm thấy kết quả
                    for col in range(table.columnCount()):
                        table.item(row, col).setBackground(QBrush(Qt.NoBrush))

            return

        # 🔹 Kiểm tra nếu từ khóa khớp với tên tab nào
        for tab_index in range(self.tabs.count()):
            tab_name = self.tabs.tabText(tab_index).strip().lower()
            if search_text in tab_name:
                self.tabs.setCurrentIndex(tab_index)
                return  # Nếu tìm thấy tab, dừng luôn (không cần tìm trong bảng)

        found_user = False  # Kiểm tra có tìm thấy trong bảng không

        # 🔹 Nếu không tìm thấy tab, tìm trong cột đầu tiên
        for tab_index in range(self.tabs.count()):
            tab = self.tabs.widget(tab_index)
            table = tab.layout().itemAt(0).widget()

            for row in range(table.rowCount()):
                item = table.item(row, 0)  # Chỉ tìm trong cột đầu tiên
                if item and search_text in item.text().strip().lower():
                    table.setRowHidden(row, False)  # Hiện dòng phù hợp
                    table.selectRow(row)  # Bôi đen dòng tìm thấy
                    # Tô màu nền của các ô trong dòng tìm thấy
                    for col in range(table.columnCount()):
                        table.item(row, col).setBackground(Qt.yellow)  # Chọn màu vàng
                    found_user = True
                else:
                    table.setRowHidden(row, True)  # Ẩn dòng không khớp
                    # Khôi phục màu nền của các ô không tìm thấy
                    for col in range(table.columnCount()):
                        table.item(row, col).setBackground(QBrush(Qt.NoBrush))


            # Nếu tìm thấy trong bảng, chuyển sang tab đó
            if found_user:
                self.tabs.setCurrentIndex(tab_index)
                break

        # 🔹 Nếu không tìm thấy gì, hiện thông báo
        if not found_user:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("Không tìm thấy")
            msg_box.setText("Không tìm thấy kết quả phù hợp.")
            msg_box.setStandardButtons(QMessageBox.Ok)

            # Hiển thị thông báo
            msg_box.show()
            QTimer.singleShot(1000, msg_box.close)  # Tự động đóng sau 1 giây
            msg_box.exec_()

            # Xóa nội dung ô tìm kiếm
            self.search_input.clear()
        
    def create_new_tab_with_data(self, tab_name, accounts):
        tab = QWidget()
        layout = QVBoxLayout()

        table = CustomTableWidget(
            row_count=len(accounts),
            context_menu_callback=self.context_menu.show_excel_menu,
            item_changed_callback=self.mark_unsaved
        )
        table.populate_with_accounts(accounts)

        layout.addWidget(table)
        tab.setLayout(layout)
        self.tabs.addTab(tab, tab_name)

    def transfer_row_to_warehouse(self, table, row):
        # Ensure warehouse window is open
        if not hasattr(self, 'warehouse_window') or self.warehouse_window is None:
            self.open_warehouse()

        # Lấy tên tab hiện tại
        tab_name = self.tabs.tabText(self.tabs.currentIndex())

        # Lấy dữ liệu của hàng
        row_data = [table.item(row, col).text() if table.item(row, col) else "" for col in range(5)]
        row_data.append(tab_name)  # Thêm tên tab vào cột 6

        # Gửi dữ liệu sang WarehouseWindow
        self.warehouse_window.add_row_with_data(row_data)
        table.removeRow(row)

        # Scroll tới dòng vừa thêm trong warehouse
        warehouse_table = self.warehouse_window.table
        last_row_index = warehouse_table.rowCount() - 1
        if last_row_index >= 0:
            warehouse_table.scrollToItem(warehouse_table.item(last_row_index, 0), QTableWidget.PositionAtCenter)
            warehouse_table.setCurrentCell(last_row_index, 0)

        # Mark as unsaved
        self.mark_unsaved()
        self.warehouse_window.mark_unsaved()

        # Save data for both Excel-like table and warehouse
        try:
            self.save_to_json()
            self.warehouse_window.save_to_json()
        except Exception as e:
            print(f"Error saving data: {e}")


    def open_warehouse(self):
            # Kiểm tra xem cửa sổ kho đã tồn tại chưa
            if not hasattr(self, 'warehouse_window') or self.warehouse_window is None:
                # Tạo cửa sổ kho và truyền tham chiếu của ExcelLikeTable
                self.warehouse_window = WarehouseWindow(parent=self, excel_table=self)
                
                # Thiết lập kết nối hai chiều
                self.warehouse_window.excel_table = self
            else:
                # Nếu cửa sổ đã tồn tại, đảm bảo kết nối vẫn được duy trì
                self.warehouse_window.excel_table = self
            
            # Hiển thị cửa sổ kho
            self.warehouse_window.show()

            # Đặt vị trí cửa sổ kho cạnh cửa sổ chính
            main_geometry = self.geometry()
            warehouse_geometry = self.warehouse_window.geometry()
            
            # Đặt cửa sổ kho ngay bên phải cửa sổ chính
            self.warehouse_window.setGeometry(
                main_geometry.x() + main_geometry.width(), 
                main_geometry.y(), 
                warehouse_geometry.width(), 
                warehouse_geometry.height()
            )





    def create_new_tab(self):
        # Lấy danh sách tên thiết bị đã kết nối
        connected_devices = self.adb.get_connected_devices()

        # Lọc ra các thiết bị đã được tạo tab (tên thiết bị đã tồn tại trong tabs)
        existing_tabs = [self.tabs.tabText(index) for index in range(self.tabs.count())]
        available_devices = [device for device in connected_devices if device not in existing_tabs]

        # Kiểm tra nếu không còn thiết bị nào có thể chọn
        if not available_devices:
            QMessageBox.warning(self, "Lỗi", "Tất cả các thiết bị đã được tạo tab!")
            return

        # Cho phép người dùng chọn thiết bị từ danh sách các thiết bị còn lại
        device_name, ok = QInputDialog.getItem(self, "Chọn thiết bị", "Chọn một thiết bị làm tên bảng:", available_devices, 0, False)

        # Nếu người dùng không chọn hoặc đóng hộp thoại
        if not ok or not device_name:
            return

        # Kiểm tra nếu tên bảng đã tồn tại (dự phòng, có thể bỏ qua vì đã lọc)
        if device_name in existing_tabs:
            QMessageBox.warning(self, "Lỗi", "Tên bảng đã tồn tại! Vui lòng chọn thiết bị khác.")
            return

        # Tạo tab mới với tên thiết bị được chọn
        tab = QWidget()
        layout = QVBoxLayout()
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["Username", "Password", "Mail", "TK Golike", "Status", "Original Tab"])
        table.setContextMenuPolicy(3)
        table.customContextMenuRequested.connect(lambda pos, tbl=table: self.show_context_menu(pos, tbl))
        table.itemChanged.connect(self.mark_unsaved)
        table.setEditTriggers(QTableWidget.DoubleClicked)

        # Set row height for all rows
        table.verticalHeader().setDefaultSectionSize(40)  # Adjust this value to change all row heights

        layout.addWidget(table)
        tab.setLayout(layout)

        # Thêm tab mới vào tabs với tên là tên thiết bị
        self.tabs.addTab(tab, device_name)

        # Chuyển tới tab vừa tạo
        tab_index = self.tabs.indexOf(tab)
        self.tabs.setCurrentIndex(tab_index)

        # Đánh dấu trạng thái chưa lưu
        self.mark_unsaved()




    def close_tab(self, index):
        """Đóng tab khi nhấn vào nút đóng và xóa dữ liệu khỏi JSON"""
        tab_name = self.tabs.tabText(index)  # Lấy tên tab

        reply = QMessageBox.question(self, "Xác nhận",
                                    f"Bạn có chắc chắn muốn đóng tab '{tab_name}' và xóa toàn bộ dữ liệu?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.tabs.removeTab(index)  # Xóa tab

            # Xóa dữ liệu của tab khỏi JSON
            self.remove_tab_data_from_json(tab_name)

            # Đánh dấu dữ liệu đã thay đổi
            self.mark_unsaved()

    def remove_tab_data_from_json(self, tab_name, filename="data/data.json"):
        """Xóa dữ liệu của tab khỏi file JSON"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            if tab_name in data:
                del data[tab_name]  # Xóa dữ liệu của tab

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"Dữ liệu của tab '{tab_name}' đã bị xóa khỏi JSON.")
        except FileNotFoundError:
            print("Không tìm thấy file JSON.")
        except json.JSONDecodeError:
            print("Lỗi khi đọc JSON.")


    def mark_unsaved(self):
        """Đánh dấu dữ liệu đã thay đổi"""
        if not self.data_changed:
            self.setWindowTitle("Excel-like Table with Context Menu *")
            self.data_changed = True
    
    def create_menu_action(self, menu, text, tooltip, icon_path=None, enabled=True):
        """
        Create a menu action with hover tooltip and optional icon
        
        :param menu: Parent menu
        :param text: Action text
        :param tooltip: Tooltip text to show on hover
        :param icon_path: Optional path to icon
        :param enabled: Whether the action is enabled
        :return: QAction
        """
        action = QAction(text, menu)
        action.setToolTip(tooltip)
        
        # Set icon if path is provided
        if icon_path:
            action.setIcon(QIcon(icon_path))
        
        # Set enabled/disabled state
        action.setEnabled(enabled)
        
        return action




    def get_tab_data(self, table):
        """Lấy toàn bộ dữ liệu trong một tab dưới dạng danh sách các dictionary"""
        data = []
        
        # Tìm tên tab chứa bảng hiện tại
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if tab.layout().itemAt(0).widget() == table:
                tab_name = self.tabs.tabText(index)
                break
        else:
            tab_name = "Unknown"

        # Duyệt từng hàng để lấy dữ liệu
        for row in range(table.rowCount()):
            row_data = {
                table.horizontalHeaderItem(col).text(): table.item(row, col).text() if table.item(row, col) else ""
                for col in range(table.columnCount())
            }
            row_data["Tab Name"] = tab_name  # Thêm tên tab vào dữ liệu
            data.append(row_data)

        return data


    def get_row_data(self, table, row):
        """Lấy dữ liệu của một hàng dưới dạng dictionary, kèm theo tên tab"""
        if row < 0:
            return {}

        # Tìm tên tab chứa bảng hiện tại
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            if tab.layout().itemAt(0).widget() == table:
                tab_name = self.tabs.tabText(index)
                break
        else:
            tab_name = "Unknown"

        row_data = {
            table.horizontalHeaderItem(col).text(): table.item(row, col).text() if table.item(row, col) else ""
            for col in range(table.columnCount())
        }

        # Thêm tên tab vào dữ liệu
        row_data["Tab Name"] = tab_name
        return row_data

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ExcelLikeTable()
    window.show()
    sys.exit(app.exec_())
