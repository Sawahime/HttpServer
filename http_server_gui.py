import http.server
import socketserver
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import webbrowser

class SimpleHTTPServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Louis HTTP Server")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 状态
        self.server = None
        self.server_thread = None
        self.running = False

        # 设置界面
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Server Path:").grid(row=0, column=0, sticky=tk.W)
        self.dir_entry = ttk.Entry(main_frame, width=50)
        self.dir_entry.grid(row=0, column=1, sticky=tk.EW)

        # 设置默认目录为 .exe 所在目录或上级目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(sys.executable), ".."))
        else:
            base_dir = os.path.abspath("D:/dev/Python Script/Server")
        self.dir_entry.insert(0, base_dir)

        browse_btn = ttk.Button(main_frame, text="Browse...", command=self.browse_directory)
        browse_btn.grid(row=0, column=2, padx=(5, 0))

        ttk.Label(main_frame, text="Port:").grid(row=1, column=0, sticky=tk.W)
        self.port_entry = ttk.Entry(main_frame, width=10)
        self.port_entry.grid(row=1, column=1, sticky=tk.W)
        self.port_entry.insert(0, "8686")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0))

        self.start_btn = ttk.Button(btn_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        open_btn = ttk.Button(btn_frame, text="Open index.html", command=self.open_in_browser)
        open_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(main_frame, text="Server Logs:").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.log_text = tk.Text(main_frame, height=10, width=60, state=tk.DISABLED)
        self.log_text.grid(row=4, column=0, columnspan=3, sticky=tk.NSEW)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=4, column=3, sticky=tk.NS)
        self.log_text.config(yscrollcommand=scrollbar.set)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

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

    def start_server(self):
        if self.running:
            return

        directory = self.dir_entry.get()
        if not os.path.isdir(directory):
            messagebox.showerror("Error", "The specified directory does not exist!")
            return

        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number(1-65535)")
            return

        os.chdir(directory)

        gui_ref = self  # 用于 log_message

        class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Cache-Control', 'no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                super().end_headers()

            def log_message(self, format, *args):
                gui_ref.log_message("[Request] " + format % args)

            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()

                    # 生成包含自动加载脚本的 HTML
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Network Transfer Test</title>
                        <script>
                            // 循环发送1000次
                            window.onload = function() {
                                const fixedSize = 18000; // 固定大小B
                                const totalRequests = 1000; // 发送1000次
                                let count = 0;

                                const sendRequest = () => {
                                    if (count >= totalRequests) {
                                        console.log("All requests completed!");
                                        return;
                                    }

                                    fetch(`/size/${fixedSize}`)
                                        .then(response => response.text())
                                        .then(data => {
                                            count++;
                                            console.log(`Request ${count}/${totalRequests}: Loaded ${fixedSize} bytes`);
                                            sendRequest(); // 继续发送下一个请求
                                        })
                                        .catch(err => console.error("Error:", err));
                                };

                                sendRequest(); // 开始发送请求
                            };
                        </script>
                    </head>
                    <body>
                        <h1>Network Transfer Test</h1>
                        <p>Check the browser's Network tab to see 1000 requests of 500B each.</p>
                        <div id="results"></div>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode('utf-8'))

                elif self.path.startswith('/size/'):
                    try:
                        size = int(self.path.split('/')[-1])
                        self.send_response(200)
                        self.send_header('Content-type', 'text/plain')  # 纯文本减少开销
                        self.send_header('Content-Length', str(size))
                        self.end_headers()

                        # 生成指定大小的数据（填充 'A'）
                        dummy_data = 'A' * size
                        self.wfile.write(dummy_data.encode('utf-8'))
                    except ValueError:
                        self.send_error(400, "Invalid size parameter")

                else:
                    # 其他请求（如 index.html）仍然走默认处理
                    super().do_GET()

        try:
            self.server = socketserver.TCPServer(("", port), NoCacheHTTPRequestHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

            self.running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

            self.log_message(f"Server started on port {port}")
            self.log_message(f"Serving directory: {directory}")
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

            self.log_message("Server stopped")

    def open_in_browser(self):
        if not self.running:
            messagebox.showwarning("Warning", "Please start the server first")
            return

        try:
            port = int(self.port_entry.get())
            webbrowser.open(f"http://localhost:{port}/index.html")
        except:
            pass

    def on_close(self):
        if self.running:
            self.stop_server()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleHTTPServerGUI(root)
    root.mainloop()



