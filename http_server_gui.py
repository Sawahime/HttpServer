import http.server
import socketserver
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import re


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, gui_ref=None, **kwargs):
        self.gui_ref = gui_ref
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # 获取 GUI 设置的参数
            packet_size = self.gui_ref.packet_size if self.gui_ref else 1000
            request_times = self.gui_ref.request_times if self.gui_ref else 10

            # 生成 HTML 页面，包含自动请求的 JavaScript 代码
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Network Test Page</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .progress-container {{ 
                        width: 100%; 
                        background-color: #f1f1f1; 
                        border-radius: 5px; 
                        margin: 10px 0;
                    }}
                    .progress-bar {{
                        width: 0%; 
                        height: 30px; 
                        background-color: #4CAF50;
                        border-radius: 5px; 
                        text-align: center;
                        line-height: 30px;
                        color: white;
                    }}
                    .results {{ 
                        margin-top: 20px; 
                        padding: 10px; 
                        border: 1px solid #ddd; 
                        border-radius: 5px;
                    }}
                </style>
            </head>
            <body>
                <h1>Network Test Page</h1>
                <div class="progress-container">
                    <div id="progressBar" class="progress-bar">0%</div>
                </div>
                <div id="results" class="results"></div>

                <script>
                    const packetSize = {packet_size};
                    const requestTimes = {request_times};
                    const resultsDiv = document.getElementById('results');
                    const progressBar = document.getElementById('progressBar');

                    let successfulRequests = 0;
                    let failedRequests = 0;
                    let totalResponseSize = 0;
                    let startTime = Date.now();

                    // 发起请求
                    async function fetchData() {{
                        for (let i = 0; i < requestTimes; i++) {{
                            try {{
                                const response = await fetch(`/size/${{packetSize}}?req=${{i}}`);
                                if (response.ok) {{
                                    const data = await response.text();
                                    totalResponseSize += data.length;
                                    successfulRequests++;
                                }} else {{
                                    failedRequests++;
                                }}
                            }} catch (error) {{
                                failedRequests++;
                            }}

                            // 更新进度
                            const progress = Math.round(((i + 1) / requestTimes) * 100);
                            progressBar.style.width = progress + '%';
                            progressBar.textContent = progress + '%';

                            // 更新结果
                            updateResults();
                        }}
                    }}

                    // 更新结果
                    function updateResults() {{
                        const elapsedTime = (Date.now() - startTime) / 1000; // 秒
                        const avgSpeed = totalResponseSize / elapsedTime / 1024; // KB/s

                        resultsDiv.innerHTML = `
                            <h3>Test Results</h3>
                            <p><strong>Successful Requests:</strong> ${{successfulRequests}}</p>
                            <p><strong>Failed Requests:</strong> ${{failedRequests}}</p>
                            <p><strong>Total Data Received:</strong> ${{(totalResponseSize / 1024).toFixed(2)}} KB</p>
                            <p><strong>Average Speed:</strong> ${{avgSpeed.toFixed(2)}} KB/s</p>
                            <p><strong>Time Elapsed:</strong> ${{elapsedTime.toFixed(2)}} seconds</p>
                        `;
                    }}

                    // 开始测试
                    fetchData();
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
            return

        # 处理 /size/<packet_size> 请求
        elif self.path.startswith("/size/"):
            try:
                packet_size = int(self.path.split("/")[2].split("?")[0])
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                # 返回指定大小的数据（这里用随机数据模拟）
                self.wfile.write(b"X" * packet_size)
            except ValueError:
                self.send_error(400, "Invalid packet size")
            return

        else:
            self.send_error(404, "File not found")

    def end_headers(self):
        # 添加禁止缓存的头信息
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        message = format % args
        if self.gui_ref:
            self.gui_ref.log_request(message)


class SimpleHTTPServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Louis HTTP Server")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 状态
        self.server = None
        self.server_thread = None
        self.running = False
        self.packet_size = 1000  # 默认包大小
        self.request_times = 10  # 传输次数
        self.lock = threading.Lock()  # 用于线程安全的包大小修改
        self.request_count = 0  # 请求计数器, 用于log

        # 设置界面
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 服务器设置部分
        settings_frame = ttk.LabelFrame(main_frame, text="Server Settings", padding="5")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))

        ttk.Label(settings_frame, text="Port:").grid(row=0, column=0, sticky=tk.W)
        self.port_entry = ttk.Entry(settings_frame, width=10)
        self.port_entry.grid(row=0, column=1, sticky=tk.W)
        self.port_entry.insert(0, "8686")

        # 测试参数部分
        test_frame = ttk.LabelFrame(main_frame, text="Test Parameters", padding="5")
        test_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))

        ttk.Label(test_frame, text="Packet Size (B):").grid(
            row=0, column=0, sticky=tk.W
        )
        self.size_entry = ttk.Entry(test_frame, width=10)
        self.size_entry.grid(row=0, column=1, sticky=tk.W)
        self.size_entry.insert(0, str(self.packet_size))

        ttk.Label(test_frame, text="Request Times:").grid(row=1, column=0, sticky=tk.W)
        self.times_entry = ttk.Entry(test_frame, width=10)
        self.times_entry.grid(row=1, column=1, sticky=tk.W)
        self.times_entry.insert(0, str(self.request_times))

        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))

        # 启动按钮
        self.start_btn = ttk.Button(
            btn_frame, text="Start Server", command=self.start_server
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        # 停止按钮
        self.stop_btn = ttk.Button(
            btn_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # 打开本地网页按钮
        self.open_btn = ttk.Button(
            btn_frame,
            text="Open Page",
            command=self.open_test_page,
            state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT, padx=5)

        # 更新设置按钮
        self.update_btn = ttk.Button(
            btn_frame,
            text="Update Settings",
            command=self.update_settings,
            state=tk.NORMAL,
        )
        self.update_btn.pack(side=tk.LEFT, padx=5)

        # 创建日志框架
        logs_frame = ttk.Frame(main_frame)
        logs_frame.grid(row=3, column=0, columnspan=2, pady=(0, 0), sticky=tk.NSEW)

        # 服务器日志
        ttk.Label(logs_frame, text="Server Logs:").grid(row=0, column=0, sticky=tk.W)
        self.log_text = tk.Text(logs_frame, height=10, width=40, state=tk.DISABLED)
        self.log_text.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 5))

        # 请求日志
        ttk.Label(logs_frame, text="Request Logs:").grid(row=0, column=2, sticky=tk.W)
        self.request_log_text = tk.Text(
            logs_frame, height=10, width=40, state=tk.DISABLED
        )
        self.request_log_text.grid(row=1, column=2, sticky=tk.NSEW)

        # 服务器日志滚动条
        log_scrollbar = ttk.Scrollbar(
            logs_frame, orient=tk.VERTICAL, command=self.log_text.yview
        )
        log_scrollbar.grid(row=1, column=1, sticky=tk.NS)
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        # 请求日志滚动条
        req_scrollbar = ttk.Scrollbar(
            logs_frame, orient=tk.VERTICAL, command=self.request_log_text.yview
        )
        req_scrollbar.grid(row=1, column=3, sticky=tk.NS)
        self.request_log_text.config(yscrollcommand=req_scrollbar.set)

        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.columnconfigure(1, weight=1)
        logs_frame.rowconfigure(1, weight=1)

    def start_server(self):
        if self.running:
            return

        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number(1-65535)")
            return

        # 在启动服务器前更新设置
        self.update_settings()

        self.request_count = 0  # 重置请求计数器

        handler = lambda *args: NoCacheHTTPRequestHandler(*args, gui_ref=self)

        try:
            self.server = socketserver.TCPServer(("", port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

            self.running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.open_btn.config(state=tk.NORMAL)

            self.log_message(f"Server started on port {port}")
            self.log_message(f"Packet size: {self.packet_size}B")
            self.log_message(f"Request times: {self.request_times}")

        except Exception as e:
            messagebox.showerror("Error", f"The server cannot be started.: {str(e)}")

    def stop_server(self):
        if self.running and self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join()

            self.running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.open_btn.config(state=tk.DISABLED)

            self.log_message("Server stopped")

    def open_test_page(self):
        if not self.running:
            messagebox.showwarning("Warning", "Server is not running")
            return

        try:
            port = int(self.port_entry.get())
            url = f"http://localhost:{port}/"

            # 尝试以无痕模式打开（不同浏览器支持不同方式）
            chrome_path = None
            edge_path = None
            firefox_path = None

            # 检查浏览器是否安装
            try:
                import winreg  # Windows 注册表查找浏览器路径

                # 查找 Chrome
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\\Microsoft\Windows\\CurrentVersion\\App Paths\\chrome.exe",
                ) as key:
                    chrome_path = winreg.QueryValue(key, None)
                # 查找 Edge
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\\Microsoft\Windows\\CurrentVersion\\App Paths\\msedge.exe",
                ) as key:
                    edge_path = winreg.QueryValue(key, None)
            except ImportError:
                pass  # 非 Windows 系统，使用默认方式
            except FileNotFoundError:
                pass  # 浏览器未安装

            if edge_path:
                import subprocess

                subprocess.Popen([edge_path, "-inprivate", url])
            elif chrome_path:
                import subprocess

                subprocess.Popen([chrome_path, "--incognito", url])
            elif firefox_path := webbrowser.get("firefox"):
                import subprocess

                subprocess.Popen([firefox_path, "--private-window", url])
            else:
                webbrowser.open(url)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open test page: {str(e)}")

    def update_settings(self):
        """更新包大小和请求次数设置"""
        try:
            new_size = int(self.size_entry.get())
            new_times = int(self.times_entry.get())

            if new_size <= 0 or new_times <= 0:
                raise ValueError("Values must be positive")

            with self.lock:
                self.packet_size = new_size
                self.request_times = new_times

            self.log_message(
                f"Updated settings - Packet Size: {new_size}B, Request Times: {new_times}"
            )
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")

    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def log_request(self, message):
        # 从请求消息中提取大小信息
        size_match = re.search(r"/size/(\d+)", message)
        size = size_match.group(1) if size_match else "N/A"

        self.request_count += 1
        formatted_message = (
            f"[Request{self.request_count}, {size}B] {message.split(' ')[1]}"
        )

        self.request_log_text.config(state=tk.NORMAL)
        self.request_log_text.insert(tk.END, formatted_message + "\n")
        self.request_log_text.see(tk.END)
        self.request_log_text.config(state=tk.DISABLED)

    def on_close(self):
        if self.running:
            self.stop_server()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleHTTPServerGUI(root)
    root.mainloop()
