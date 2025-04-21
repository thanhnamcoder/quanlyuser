from PyQt5.QtCore import QThread, pyqtSignal
import requests
import time
from datetime import datetime, timedelta
import pytz
import re 
import uiautomator2 as u2
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import shlex
from mailTm import MailTM

DEFAULT_PASSWORD = "Nguyen2004nam@"
class MultiDeviceRunner:
    def __init__(self, devices, email=None):
        """
        Khởi tạo MultiDeviceRunner.

        Args:
            devices (list): Danh sách device_id.
            email (str): Email (chỉ dùng cho task_type = "code").
        """
        self.devices = devices
        self.email = email
        self.adb_module = AdbModule()
        self._stop_event = threading.Event()
        self.thread = None


    def run_in_background(self):
        """
        Hàm này sẽ chạy các nhiệm vụ trên các thiết bị trong một luồng riêng biệt
        để không ảnh hưởng đến ứng dụng chính.
        """
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join()
    def run(self):
        """
        Hàm chính để thực hiện các hành động trên tất cả thiết bị cùng lúc.
        Lặp lại liên tục: sau mỗi vòng chạy hết tất cả nhiệm vụ, đợi 2 giây rồi chạy lại.
        """
        while not self._stop_event.is_set():  # ✅ Sửa tại đây
            print("Bắt đầu vòng nhiệm vụ mới...")

            with ThreadPoolExecutor(max_workers=len(self.devices)) as executor:
                future_to_device = {
                    executor.submit(self.run_tasks_on_device, device_id): device_id
                    for device_id in self.devices
                }

                for future in as_completed(future_to_device):
                    device_id = future_to_device[future]
                    try:
                        result = future.result()
                        print(f"[{device_id}] {result}")
                    except Exception as e:
                        print(f"[{device_id}] Lỗi khi thực hiện nhiệm vụ trên {device_id}: {e}")

            print("Đã hoàn thành tất cả nhiệm vụ, chờ 2 giây trước khi tiếp tục...\n")
            time.sleep(2)

        print("🛑 Đã dừng MultiDeviceRunner.")



    def run_tasks_on_device(self, device_id):
        """
        Chạy các nhiệm vụ cho từng thiết bị: nhấn home, click comment button, v.v.
        
        Args:
            device_id (str): ID của thiết bị Android.
        """
        try:
            # Nhấn nút Comment
            # comment_result = self.click_comment_button(device_id)
            self.press_home_on_device(device_id)
            # print(f"[{device_id}] {comment_result}")

            return f"Hoàn thành nhiệm vụ trên {device_id}"
        except Exception as e:
            return f"Lỗi khi thực hiện nhiệm vụ trên {device_id}: {e}"

    def press_home_on_device(self, device_id):
        """
        Nhấn nút Home trên thiết bị Android.

        Args:
            device_id (str): ID của thiết bị Android.
        """
        try:
            # Kết nối với thiết bị qua uiautomator2
            device = u2.connect(device_id)
            # Nhấn nút Home
            device.press("home")
            return f"Đã nhấn nút Home trên thiết bị {device_id}."
        except Exception as e:
            raise Exception(f"Lỗi khi nhấn nút Home trên {device_id}: {e}")

    def click_comment_button(self, device_id):
        """
        Tìm và click vào button có contentDescription='Đăng bình luận' trong FrameLayout index=3, sau đó bấm back 3 lần, cách nhau 1 giây.
        
        Args:
            device_id (str): ID của thiết bị Android.
        """
        try:
            # Kết nối với thiết bị qua uiautomator2
            device = u2.connect(device_id)

            # Tìm FrameLayout chứa nút 'Đăng bình luận'
            frame_layout = device.xpath('//android.widget.FrameLayout[@index="3"]')
            if frame_layout.exists:
                buttons = frame_layout.child('//android.widget.Button')

                for button in buttons.all():
                    info = button.info
                    content_desc = info.get("contentDescription", "")

                    if content_desc == "Đăng bình luận":
                        print(f"[{device_id}] Tìm thấy nút 'Đăng bình luận', đợi 2 giây trước khi click...")
                        time.sleep(2)  # Đợi 2 giây trước khi click
                        button.click()
                        print(f"[{device_id}] Đã click vào nút 'Đăng bình luận'")
                        
                        # Bấm back 3 lần sau khi click
                        for _ in range(3):
                            device.press("back")
                            time.sleep(1)  # Đợi 1 giây giữa mỗi lần back
                        
                        return "Nút 'Đăng bình luận' đã được click và back 3 lần."
            else:
                return f"[{device_id}] Không tìm thấy FrameLayout index=3 hoặc nút 'Đăng bình luận'."
        except Exception as e:
            return f"[{device_id}] Lỗi khi tìm và click nút 'Đăng bình luận': {e}"


class AdbModule:
    """
    Module quản lý các thao tác với ADB và uiautomator2
    """
    
    def __init__(self):
        """
        Khởi tạo AdbModule
        """
        # Thiết lập logging
        self.logger = logging.getLogger("AdbModule")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)


    def paste_text_to_device(self, text, device_id):
        # Lấy nội dung từ QLineEdit
        text_to_paste = text
        
        # Thay thế khoảng trắng bằng '%s'
        text_to_paste = text_to_paste.replace(' ', '%s')
        
        # Xử lý các ký tự đặc biệt và dấu tiếng Việt
        special_chars = {
            'á': 'a\u0301', 'à': 'a\u0300', 'ả': 'a\u0309', 'ã': 'a\u0303', 'ạ': 'a\u0323',
            'ắ': 'ă\u0301', 'ằ': 'ă\u0300', 'ẳ': 'ă\u0309', 'ẵ': 'ă\u0303', 'ặ': 'ă\u0323',
            'ấ': 'â\u0301', 'ầ': 'â\u0300', 'ẩ': 'â\u0309', 'ẫ': 'â\u0303', 'ậ': 'â\u0323',
            'é': 'e\u0301', 'è': 'e\u0300', 'ẻ': 'e\u0309', 'ẽ': 'e\u0303', 'ẹ': 'e\u0323',
            'ế': 'ê\u0301', 'ề': 'ê\u0300', 'ể': 'ê\u0309', 'ễ': 'ê\u0303', 'ệ': 'ê\u0323',
            'í': 'i\u0301', 'ì': 'i\u0300', 'ỉ': 'i\u0309', 'ĩ': 'i\u0303', 'ị': 'i\u0323',
            'ó': 'o\u0301', 'ò': 'o\u0300', 'ỏ': 'o\u0309', 'õ': 'o\u0303', 'ọ': 'o\u0323',
            'ố': 'ô\u0301', 'ồ': 'ô\u0300', 'ổ': 'ô\u0309', 'ỗ': 'ô\u0303', 'ộ': 'ô\u0323',
            'ớ': 'ơ\u0301', 'ờ': 'ơ\u0300', 'ở': 'ơ\u0309', 'ỡ': 'ơ\u0303', 'ợ': 'ơ\u0323',
            'ú': 'u\u0301', 'ù': 'u\u0300', 'ủ': 'u\u0309', 'ũ': 'u\u0303', 'ụ': 'u\u0323',
            'ứ': 'ư\u0301', 'ừ': 'ư\u0300', 'ử': 'ư\u0309', 'ữ': 'ư\u0303', 'ự': 'ư\u0323',
            'ý': 'y\u0301', 'ỳ': 'y\u0300', 'ỷ': 'y\u0309', 'ỹ': 'y\u0303', 'ỵ': 'y\u0323',
        }
        
        # Chuyển đổi các ký tự đặc biệt
        for char in special_chars:
            text_to_paste = text_to_paste.replace(char, special_chars[char])
            text_to_paste = text_to_paste.replace(char.upper(), special_chars[char].upper())

        try:
            # Dán nội dung vào thiết bị qua ADB
            process = subprocess.run(
                ["adb", "-s", device_id, "shell", "input", "text", text_to_paste],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            # Nếu có khoảng trắng, thêm lệnh space
            if '%s' in text_to_paste:
                time.sleep(0.5)
                spaces = text_to_paste.count('%s')
                for _ in range(spaces):
                    subprocess.run(
                        ["adb", "-s", device_id, "shell", "input", "keyevent", "62"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    time.sleep(0.2)
                    
        except subprocess.TimeoutExpired:
            print("ADB command timed out")
        except Exception as e:
            print(f"Error: {str(e)}")
            
        time.sleep(1)


    def get_username(self, device_id):
        """
        Lấy username từ thiết bị với tốc độ tìm kiếm được tối ưu
        
        Args:
            device_id (str): ID của thiết bị Android
            
        Returns:
            str: Username bắt đầu bằng '@' (đã loại bỏ '@'), 
                hoặc None nếu không tìm thấy
        """
        try:
            device = u2.connect(device_id)
            
            # Tìm layout với timeout
            layout = device(className="android.widget.LinearLayout", instance=2)
            if not layout.exists:
                self.logger.warning(f"Không tìm thấy LinearLayout trên thiết bị {device_id}")
                return None
                
            # Tối ưu tìm kiếm text
            children = layout.child()
            
            # Tìm nhanh với generator expression
            for child in children:
                if text := child.info.get('text'):
                    if text.startswith('@'):
                        username = text.lstrip('@')
                        self.logger.info(f"Đã tìm thấy username: {username}")
                        return username  # Trả về username đầu tiên tìm thấy
            
            self.logger.warning(f"Không tìm thấy text bắt đầu bằng '@' trên thiết bị {device_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy username từ thiết bị {device_id}: {e}")
            return None
    def get_connected_devices(self):
        """
        Lấy danh sách tất cả các thiết bị được kết nối qua ADB.
        
        :return: Danh sách các thiết bị, mỗi thiết bị là một tuple gồm (device_id, device_name)
        """
        try:
            # Chạy lệnh adb devices để lấy danh sách thiết bị
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            
            # Kiểm tra nếu có lỗi khi chạy lệnh
            if result.returncode != 0:
                raise Exception("ADB command failed")

            # Lọc các thiết bị từ đầu ra của lệnh adb devices
            devices = []
            for line in result.stdout.splitlines():
                if line.strip() and line != "List of devices attached":
                    device_id = line.split()[0]  # Device ID ở cột đầu tiên
                    device_name = line.split()[1] if len(line.split()) > 1 else ""  # Nếu có tên thiết bị
                    devices.append((device_id))

            return devices
        except Exception as e:
            print(f"Lỗi khi lấy danh sách thiết bị ADB: {e}")
            return []
class RunThread(QThread):
    finished_signal = pyqtSignal(object)

    def __init__(self, task_type="code", email=None, username=None, adb_module=None, device_id=None, parent=None):
        super().__init__(parent)
        self.task_type = task_type
        self.email = email
        self.username = username
        self.adb_module = adb_module
        self.device_id = device_id
        self.mail_tm = MailTM()
        self.is_running = True  # ✅ Cần dòng này ở đây

    def run(self):
        if self.task_type == "code":
            self.run_get_code()

        elif self.task_type == "username":
            self.run_get_username()

        elif self.task_type == "email":
            result = self.run_get_mail()  # Gọi và lưu kết quả
            self.finished_signal.emit(result)  # Emit dict

        else:
            self.finished_signal.emit({
                "status": "error",
                "message": "❌ Nhiệm vụ không hợp lệ.",
                "email": ""
            })


    def create_email_account(self, username):
        """
        Tạo địa chỉ email mới từ username
        """
        default_password = "Nguyen2004nam@"

        try:
            domain = self.mail_tm.get_domains()
            if not domain:
                return {"status": "error", "message": "Không thể lấy domain từ API mail.tm!"}

            clean_username = username.replace('.', '')
            new_email = f"{clean_username}@{domain}"

            result = self.mail_tm.create_account(new_email, default_password)

            response = {
                "status": result,
                "email": new_email,
                "password": default_password,
            }

            if result == "created":
                response["message"] = f"✅ Đã tạo tài khoản email: {new_email}"
            elif result == "exists":
                response["message"] = f"⚠️ Email {new_email} đã tồn tại."
            elif result == "too_many_requests":
                response["message"] = "⛔ Quá nhiều yêu cầu. Vui lòng thử lại sau."
            else:
                response["message"] = f"❌ Không thể tạo tài khoản email: {new_email}"

            return response

        except Exception as e:
            print("Lỗi khi tạo email:", e)
            return {
                "status": "error",
                "message": f"❌ Lỗi khi tạo email: {str(e)}"
            }


    def run_get_mail(self):
        if not self.username:
            return {
                "status": "error",
                "message": "⚠️ Không có username.",
                "email": ""
            }

        print(f"[RUN] Đang tạo email cho username: {self.username}")
        mail = self.create_email_account(self.username)
        return mail  # Trả về dict


            
    def run_get_code(self):
        if not self.email:
            self.finished_signal.emit("Không có email.")
            return

        print(self.email)
        password = "Nguyen2004nam@"  # Mặc định, nên cho truyền vào nếu có thể
        token = self.mail_tm.get_token(self.email, password)

        if token:
            print(f"Token đã được lấy: {token}")
            key = self.fetch_emails_multiple_times(token)
            if key:
                self.finished_signal.emit(key)
            else:
                self.finished_signal.emit("Không thể tìm thấy mã số 6 chữ số!")
        else:
            self.finished_signal.emit("Không thể lấy token từ email!")

    def run_get_username(self):
        if not self.device_id or not self.adb_module:
            self.finished_signal.emit("Thiết bị không hợp lệ.")
            return

        username = self.adb_module.get_username(self.device_id)
        self.finished_signal.emit(username)



    def fetch_emails_multiple_times(self, token):
        """
        Lấy danh sách email trong vòng 5 phút gần nhất và trả về mã số 6 chữ số đầu tiên tìm được.
        """
        for i in range(5):
            print(f"Lần gọi thứ {i+1}:")
            subjects = self.mail_tm.get_emails(token)

            if subjects:
                # Sử dụng regular expression để trích xuất mã số 6 chữ số
                numbers = [re.findall(r'\d{6}', subject) for subject in subjects]
                numbers = [item for sublist in numbers for item in sublist]  # Kết hợp các số lại thành một danh sách phẳng

                if numbers:
                    key = numbers[0]  # Lấy mã số đầu tiên tìm được
                    return key
            if not self.is_running:
                return "Quá trình bị hủy!"
            time.sleep(1)

    def stop(self):
        """
        Dừng quá trình khi cần.
        """
        self.is_running = False