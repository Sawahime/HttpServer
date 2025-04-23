import http.server
import socketserver
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import webbrowser
import re


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, gui_ref=None, **kwargs):
        self.gui_ref = gui_ref
        super().__init__(*args, **kwargs)
    
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        message = format % args
        if '/size/' in message and self.gui_ref:  # 只记录/size/请求
            self.gui_ref.log_request(message)

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # 使用锁获取当前包大小
            with self.gui_ref.lock:
                current_size = self.gui_ref.packet_size

            # 生成包含自动加载脚本的 HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Network Transfer Test</title>
                <script>
                    window.onload = function() {{
                        const fixedSize = {current_size};
                        const totalRequests = 1000;
                        let count = 0;

                        const sendRequest = () => {{
                            if (count >= totalRequests) return;
                            fetch(`/size/${{fixedSize}}?_=${{Date.now()}}`)
                                .then(response => response.text())
                                .then(data => {{
                                    count++;
                                    sendRequest();
                                }})
                                .catch(err => console.error("Error:", err));
                        }};
                        sendRequest();
                    }};
                </script>
            </head>
            <body>
                <h1>Network Transfer Test</h1>
                <p>Check the browser's Network tab to see 1000 requests of {current_size}B each.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path.startswith('/size/'):
            try:
                size = int(self.path.split('/')[2].split('?')[0])
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Content-Length', str(size))
                self.end_headers()
                self.wfile.write(('A' * size).encode('utf-8'))
            except ValueError:
                self.send_error(400, "Invalid size parameter")
        else:
            super().do_GET()


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
        self.lock = threading.Lock()  # 用于线程安全的包大小修改
        self.request_count = 0  # 请求计数器

        # 设置界面
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ttk.Label(main_frame, text="Server Path:").grid(row=0, column=0, sticky=tk.W)
        # self.dir_entry = ttk.Entry(main_frame, width=50)
        # self.dir_entry.grid(row=0, column=1, sticky=tk.EW)

        # 设置默认目录为 .exe 所在目录或上级目录
        # if getattr(sys, 'frozen', False):
        #     base_dir = os.path.abspath(os.path.join(os.path.dirname(sys.executable), ".."))
        # else:
        #     base_dir = os.path.abspath("D:/dev/Python Script/Server")
        # self.dir_entry.insert(0, base_dir)

        # browse_btn = ttk.Button(main_frame, text="Browse...", command=self.browse_directory)
        # browse_btn.grid(row=0, column=2, padx=(5, 0))

        ttk.Label(main_frame, text="Port:").grid(row=1, column=0, sticky=tk.W)
        self.port_entry = ttk.Entry(main_frame, width=10)
        self.port_entry.grid(row=1, column=1, sticky=tk.W)
        self.port_entry.insert(0, "8686")

        # 添加包大小设置
        ttk.Label(main_frame, text="Packet Size (B):").grid(row=2, column=0, sticky=tk.W)
        self.packet_size_entry = ttk.Entry(main_frame, width=10)
        self.packet_size_entry.grid(row=2, column=1, sticky=tk.W)
        self.packet_size_entry.insert(0, "1000")
        
        # 添加更新包大小按钮
        self.update_btn = ttk.Button(main_frame, text="Update Size", command=self.update_packet_size, state=tk.DISABLED)
        self.update_btn.grid(row=2, column=2, padx=(5, 0))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))

        self.start_btn = ttk.Button(btn_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # 创建日志框架
        logs_frame = ttk.Frame(main_frame)
        logs_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky=tk.NSEW)

        # 服务器日志
        ttk.Label(logs_frame, text="Server Logs:").grid(row=0, column=0, sticky=tk.W)
        self.log_text = tk.Text(logs_frame, height=10, width=40, state=tk.DISABLED)
        self.log_text.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 5))

        # 请求日志
        ttk.Label(logs_frame, text="Request Logs:").grid(row=0, column=1, sticky=tk.W)
        self.request_log_text = tk.Text(logs_frame, height=10, width=40, state=tk.DISABLED)
        self.request_log_text.grid(row=1, column=1, sticky=tk.NSEW)

        # 滚动条
        log_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=1, column=2, sticky=tk.NS)
        self.log_text.config(yscrollcommand=log_scrollbar.set)

        req_scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.request_log_text.yview)
        req_scrollbar.grid(row=1, column=3, sticky=tk.NS)
        self.request_log_text.config(yscrollcommand=req_scrollbar.set)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.columnconfigure(1, weight=1)
        logs_frame.rowconfigure(1, weight=1)

    def browse_directory(self):
        dir_path = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if dir_path:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, dir_path)

    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def log_request(self, message):
        # 从请求消息中提取大小信息
        size_match = re.search(r'/size/(\d+)', message)
        size = size_match.group(1) if size_match else "N/A"
        
        self.request_count += 1
        formatted_message = f"[Request{self.request_count}, {size}B] {message.split(' ')[1]}"
        
        self.request_log_text.config(state=tk.NORMAL)
        self.request_log_text.insert(tk.END, formatted_message + "\n")
        self.request_log_text.see(tk.END)
        self.request_log_text.config(state=tk.DISABLED)

    def update_packet_size(self):
        try:
            new_size = int(self.packet_size_entry.get())
            if new_size <= 0:
                raise ValueError
            
            with self.lock:
                self.packet_size = new_size
            
            self.log_message(f"Packet size updated to {new_size}B")
            
            # 通知客户端重新开始
            if self.running:
                try:
                    port = int(self.port_entry.get())
                    webbrowser.open(f"http://localhost:{port}/")
                except:
                    pass
                
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid packet size (positive integer)")

    def start_server(self):
        if self.running:
            return

        # directory = self.dir_entry.get()
        # if not os.path.isdir(directory):
        #     messagebox.showerror("Error", "The specified directory does not exist!")
        #     return

        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number(1-65535)")
            return

        try:
            self.packet_size = int(self.packet_size_entry.get())
            if self.packet_size <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid packet size (positive integer)")
            return

        # os.chdir(directory)
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
            self.update_btn.config(state=tk.NORMAL)

            self.log_message(f"Server started on port {port}")
            # self.log_message(f"Serving directory: {directory}")
            self.log_message(f"Initial packet size: {self.packet_size}B")
            self.log_message(f"Visit: http://localhost:{port}/")

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
            self.update_btn.config(state=tk.DISABLED)

            self.log_message("Server stopped")

    def on_close(self):
        if self.running:
            self.stop_server()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleHTTPServerGUI(root)
    root.mainloop()