import requests
from datetime import datetime, timedelta
import pytz

BASE_URL = "https://api.mail.tm"

class MailTM:
    def __init__(self):
        self.base_url = BASE_URL

    def get_token(self, email, password):
        """
        Lấy token bằng cách gửi yêu cầu POST đến /token
        """
        try:
            login_url = f"{self.base_url}/token"
            credentials = {
                "address": email,
                "password": password
            }
            response = requests.post(login_url, json=credentials)
            if response.status_code == 200:
                token = response.json().get("token")
                return token
            else:
                print("Lỗi đăng nhập:", response.json())
                return None
        except Exception as e:
            print("Lỗi xảy ra khi lấy token:", e)
            return None

    def get_emails(self, token):
        """
        Lấy danh sách email trong vòng 5 phút gần nhất và trả về các subject
        """
        try:
            messages_url = f"{self.base_url}/messages"
            headers = {
                "Authorization": f"Bearer {token}"
            }
            response = requests.get(messages_url, headers=headers)
            
            if response.status_code == 200:
                messages = response.json().get("hydra:member", [])
                current_time = datetime.now(pytz.UTC)
                five_minutes_ago = current_time - timedelta(minutes=5)
                
                subjects = []
                for message in messages:
                    created_at = datetime.fromisoformat(message["createdAt"].replace('Z', '+00:00'))
                    if created_at >= five_minutes_ago:
                        subjects.append(message["subject"])
                return subjects
            else:
                print("Không thể lấy danh sách email:", response.json())
                return []
        except Exception as e:
            print("Lỗi xảy ra khi lấy email:", e)
            return []

    def get_domains(self, page=1):
        """
        Lấy domain đầu tiên từ API
        """
        url = f"{self.base_url}/domains"
        params = {"page": page}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            domains = data.get("hydra:member", [])
            if not domains:
                print("Không có domain nào khả dụng!")
                return None

            first_domain = domains[0].get("domain")
            if not first_domain:
                print("Dữ liệu domain không hợp lệ!")
                return None
            
            return first_domain
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi lấy domain: {e}")
            return None

    def create_account(self, email, password):
        """
        Tạo tài khoản trên mail.tm
        """
        try:
            payload = {
                "address": email,
                "password": password
            }
            response = requests.post(f"{self.base_url}/accounts", json=payload)
            print("Dữ liệu trả về:", response.json())  # In ra dữ liệu trả về để kiểm tra
            if response.status_code == 201:
                return "created"
            elif response.status_code == 422:
                return "exists"
            elif response.status_code == 429:
                return "too_many_requests"
            else:
                print("Lỗi tạo tài khoản:", response.text)
                return "error"
        except Exception as e:
            print("Lỗi khi tạo tài khoản:", e)
            return "error"

