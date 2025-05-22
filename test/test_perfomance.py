import argparse
import concurrent
import requests
from concurrent.futures import ThreadPoolExecutor
import time
import random
import re # 确保导入 re 模块用于 CSRF token 提取

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000" # Django 开发服务器的地址

# 登录凭证 (你需要替换成你实际的测试账号)
LOGIN_URL = f"{BASE_URL}/login/"
USERNAME = "admin@example.com"
PASSWORD = "AU250201"

# 测试参数 (这些现在可以作为全局变量或直接在函数内定义)
# 这些 NUM_REQUESTS 和 concurrent_... 变量现在可以移动到各个测试函数内部
# 或者保留在这里作为全局配置，但需要在函数内部引用
NUM_WRITE_REQUESTS = 100
CONCURRENT_WRITERS = 10
NUM_READ_REQUESTS = 250
CONCURRENT_READERS = 50
NUM_EXPORT_REQUESTS = 50
CONCURRENT_EXPORTERS = 10

# CSRF Token 获取函数 (Django 保护)
def get_csrf_token(session, url):
    response = session.get(url)
    # 查找 CSRF Token
    # 方式1: 从表单隐藏字段
    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
    if match:
        return match.group(1)
    # 方式2: 从 cookie (如果 Django 设置了 CSRF cookie)
    return session.cookies.get('csrftoken')


# --- Core Functions ---

# 1. 模拟登录并保持会话
def get_authenticated_session():
    session = requests.Session()
    csrf_token = get_csrf_token(session, LOGIN_URL) # 先访问登录页面获取 CSRF token

    if not csrf_token:
        print(f"Error: Could not get CSRF token from {LOGIN_URL}")
        return None

    login_data = {
        "email": USERNAME,
        "password": PASSWORD,
        "csrfmiddlewaretoken": csrf_token,
        "next": "/" # 登录成功后跳转到首页
    }
    response = session.post(LOGIN_URL, data=login_data, headers={'Referer': LOGIN_URL}, allow_redirects=True)

    # 改进的登录成功判断：检查最终 URL 是否与登录 URL 不同
    if response.url != LOGIN_URL:
        print(f"User {USERNAME} logged in successfully. Final URL: {response.url}")
        return session
    else:
        print(f"Login failed for {USERNAME}. Status: {response.status_code}, Response: {response.text[:200]}...")
        # 打印完整的响应文本以便调试
        # print(f"Full Response: {response.text}")
        return None

# --- Individual Test Functions (Workers) ---

# 2. 读取测试: 访问员工列表页面
def worker_read_employee_list(user_session):
    if not user_session:
        return None, 0.0

    url = f"{BASE_URL}/employee_list/" # 替换为你的员工列表URL
    start_time = time.perf_counter()
    try:
        response = user_session.get(url)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        return response.status_code, elapsed_time
    except requests.exceptions.RequestException as e:
        # print(f"Error accessing Employee List: {e}") # 避免大量并发打印
        return None, 0.0

# 3. 写入测试: 模拟添加员工
def worker_write_add_employee(user_session):
    if not user_session:
        return None, 0.0

    url = f"{BASE_URL}/api/employees/add/" # 替换为你的添加员工API URL (POST请求)
    # 对于添加员工，通常需要先GET一次表单页面来获取最新的CSRF token
    # 或者如果您的API是纯后端API且通过CSRF Header或Token在页面加载时提供，则可能不需要再次GET
    # 这里为了演示健壮性，我们再次获取一次
    csrf_token = get_csrf_token(user_session, url)
    if not csrf_token:
        # print(f"Error: Could not get CSRF token for {url}") # 避免大量并发打印
        return None, 0.0

    employee_data = {
        "name": f"Test Employee {random.randint(1000, 9999)}",
        "employee_id": f"EMP{random.randint(10000, 99999)}",
        "email": f"test{random.randint(1000, 9999)}@example.com",
        "department": random.choice(["HR", "Engineering", "Marketing", "Sales"]),
        "position": random.choice(["Manager", "Developer", "Analyst", "Clerk"]),
        "hire_date": "2023-01-01",
        "salary": random.randint(30000, 80000),
        "status": "active",
        "phone_number": f"123-456-{random.randint(1000, 9999)}",
        "address": "123 Test St",
        "emergency_contact": "Jane Doe",
        "emergency_phone": "987-654-3210",
        "csrfmiddlewaretoken": csrf_token, # 确保包含 CSRF token
    }
    start_time = time.perf_counter()
    try:
        response = user_session.post(url, data=employee_data, headers={'Referer': url})
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        return response.status_code, elapsed_time
    except requests.exceptions.RequestException as e:
        # print(f"Error adding Employee: {e}") # 避免大量并发打印
        return None, 0.0

# 4. 导出测试: 模拟导出工资报告 (PDF/CSV)
def worker_read_export_salary_report(user_session, export_format='pdf'):
    if not user_session:
        return None, 0.0

    url = f"{BASE_URL}/export/salary/?format={export_format}" # 替换为你的导出工资报告API URL
    start_time = time.perf_counter()
    try:
        response = user_session.get(url, stream=True) # 使用 stream=True 处理大文件
        # 实际读取文件内容以模拟下载过程
        for chunk in response.iter_content(chunk_size=8192):
            pass # 模拟读取，不实际保存
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        return response.status_code, elapsed_time
    except requests.exceptions.RequestException as e:
        # print(f"Error exporting Salary Report: {e}") # 避免大量并发打印
        return None, 0.0


# --- Test Runner Functions (orchestrates concurrency and reporting) ---

def run_write_tests(session):
    print("\n--- Running Write Tests (Add Employee) ---")
    write_times = []

    with ThreadPoolExecutor(max_workers=CONCURRENT_WRITERS) as executor:
        futures = [executor.submit(worker_write_add_employee, session) for _ in range(NUM_WRITE_REQUESTS)]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            status, elapsed = future.result()
            if status == 200: # 假设成功添加返回200
                write_times.append(elapsed)
            else:
                # 仅打印失败情况，避免成功时刷屏
                print(f"Write request {i+1} failed with status {status}")

    if write_times:
        avg_write_time = sum(write_times) / len(write_times)
        print(f"- Total {len(write_times)} successful employee additions.")
        print(f"- Average write (add employee) time: {avg_write_time:.4f} seconds.")
    else:
        print("- No successful write operations recorded.")

def run_read_tests(session):
    print("\n--- Running Read Tests (Employee List) ---")
    read_times = []

    with ThreadPoolExecutor(max_workers=CONCURRENT_READERS) as executor:
        futures = [executor.submit(worker_read_employee_list, session) for _ in range(NUM_READ_REQUESTS)]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            status, elapsed = future.result()
            if status == 200:
                read_times.append(elapsed)
            else:
                # 仅打印失败情况
                print(f"Read request {i+1} failed with status {status}")

    if read_times:
        avg_read_time = sum(read_times) / len(read_times)
        print(f"- Total {len(read_times)} successful employee list reads.")
        print(f"- Average read (employee list) time: {avg_read_time:.4f} seconds.")
    else:
        print("- No successful read operations recorded.")

def run_export_tests(session):
    print("\n--- Running Report Export Tests (Salary PDF) ---")
    export_times = []

    with ThreadPoolExecutor(max_workers=CONCURRENT_EXPORTERS) as executor:
        futures = [executor.submit(worker_read_export_salary_report, session, 'pdf') for _ in range(NUM_EXPORT_REQUESTS)]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            status, elapsed = future.result()
            if status == 200:
                export_times.append(elapsed)
            else:
                # 仅打印失败情况
                print(f"Export request {i+1} failed with status {status}")

    if export_times:
        avg_export_time = sum(export_times) / len(export_times)
        print(f"- Total {len(export_times)} successful PDF exports.")
        print(f"- Average export (Salary PDF) time: {avg_export_time:.4f} seconds.")
    else:
        print("- No successful export operations recorded.")


# --- Main Execution Block ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run performance tests for Django Payroll App.")
    parser.add_argument('--write', action='store_true', help='Run write tests (Add Employee).')
    parser.add_argument('--read', action='store_true', help='Run read tests (Employee List).')
    parser.add_argument('--export', action='store_true', help='Run export tests (Salary PDF).')
    parser.add_argument('--all', action='store_true', help='Run all tests (default).')

    args = parser.parse_args()

    # 如果没有指定任何参数，默认运行所有测试
    if not any([args.write, args.read, args.export]):
        args.all = True
    print("Starting performance tests...")

    # 获取认证会话，所有测试共享一个会话
    main_session = get_authenticated_session()
    if not main_session:
        print("Failed to get an authenticated session. Exiting tests.")
        exit()

    # 根据命令行参数运行相应的测试
    if args.all or args.write:
        run_write_tests(main_session)

    if args.all or args.read:
        run_read_tests(main_session)

    if args.all or args.export:
        run_export_tests(main_session)

    print("\nPerformance tests finished.")