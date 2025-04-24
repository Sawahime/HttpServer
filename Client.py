import requests
import time
import statistics
import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


class NetworkTestClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Test Client")
        
        # 默认字体大小
        self.font_size = 10
        self.text_widgets = []
        
        # 测试结果
        self.test_results = {
            'successful_requests': 0,
            'failed_requests': 0,
            'total_data': 0,
            'latencies': [],
            'throughputs': []
        }
        
        # 设置界面
        self.setup_ui()
        
        # 创建菜单
        self.create_menu()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 服务器设置部分
        settings_frame = ttk.LabelFrame(main_frame, text="Server Settings", padding="5")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Server Address:").grid(row=0, column=0, sticky=tk.W)
        self.server_entry = ttk.Entry(settings_frame, width=25)
        self.server_entry.grid(row=0, column=1, sticky=tk.W)
        self.server_entry.insert(0, "http://localhost:8686")
        
        # 测试参数部分
        test_frame = ttk.LabelFrame(main_frame, text="Test Parameters", padding="5")
        test_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        
        ttk.Label(test_frame, text="Packet Size (B):").grid(row=0, column=0, sticky=tk.W)
        self.size_entry = ttk.Entry(test_frame, width=10)
        self.size_entry.grid(row=0, column=1, sticky=tk.W)
        self.size_entry.insert(0, "1000")
        
        ttk.Label(test_frame, text="Request Times:").grid(row=1, column=0, sticky=tk.W)
        self.times_entry = ttk.Entry(test_frame, width=10)
        self.times_entry.grid(row=1, column=1, sticky=tk.W)
        self.times_entry.insert(0, "10")
        
        ttk.Label(test_frame, text="Concurrent Threads:").grid(row=2, column=0, sticky=tk.W)
        self.threads_entry = ttk.Entry(test_frame, width=10)
        self.threads_entry.grid(row=2, column=1, sticky=tk.W)
        self.threads_entry.insert(0, "1")
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # 开始测试按钮
        self.start_btn = ttk.Button(
            btn_frame, text="Start Test", command=self.start_test
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        # 停止测试按钮
        self.stop_btn = ttk.Button(
            btn_frame, text="Stop Test", command=self.stop_test, state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除结果按钮
        self.clear_btn = ttk.Button(
            btn_frame, text="Clear Results", command=self.clear_results
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 结果展示部分
        results_frame = ttk.LabelFrame(main_frame, text="Test Results", padding="5")
        results_frame.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 10))
        
        # 文本结果
        self.results_text = tk.Text(results_frame, height=10, width=40, state=tk.DISABLED)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.text_widgets.append(self.results_text)
        
        # 图表框架
        graph_frame = ttk.LabelFrame(main_frame, text="Performance Graphs", padding="5")
        graph_frame.grid(row=3, column=1, sticky=tk.NSEW, pady=(0, 10))
        
        # 创建图表
        self.figure, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 6))
        self.figure.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        # 日志框架
        logs_frame = ttk.LabelFrame(main_frame, text="Test Logs", padding="5")
        logs_frame.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW)
        
        # 测试日志
        self.log_text = tk.Text(logs_frame, height=8, width=80, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.text_widgets.append(self.log_text)
        
        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # 测试控制变量
        self.test_running = False
        self.test_thread = None
        self.stop_requested = False
        
        # 绑定鼠标滚轮事件（按住Ctrl调整字体大小）
        self.bind_mouse_wheel()
    
    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # 字体菜单
        font_menu = tk.Menu(menubar, tearoff=0)
        font_menu.add_command(label="Increase Font Size", command=lambda: self.change_font_size(1))
        font_menu.add_command(label="Decrease Font Size", command=lambda: self.change_font_size(-1))
        font_menu.add_separator()
        font_menu.add_command(label="Reset Font Size", command=lambda: self.change_font_size(0))
        menubar.add_cascade(label="Font", menu=font_menu)
        
        self.root.config(menu=menubar)
    
    def change_font_size(self, delta):
        if delta == 0:
            # 重置为默认大小
            self.font_size = 10
        else:
            # 调整大小，限制在8-24之间
            new_size = self.font_size + delta
            if 8 <= new_size <= 24:
                self.font_size = new_size
            else:
                return
        
        # 更新所有文本部件的字体大小
        font_obj = font.Font(size=self.font_size)
        for widget in self.text_widgets:
            widget.configure(font=font_obj)
    
    def bind_mouse_wheel(self):
        # 为文本部件绑定鼠标滚轮事件
        for widget in self.text_widgets:
            widget.bind("<Control-MouseWheel>", self.on_mouse_wheel)
            widget.bind("<Configure>", self.on_text_configure)
    
    def on_mouse_wheel(self, event):
        # 按住Ctrl键时滚动鼠标滚轮调整字体大小
        if event.state & 0x0004:  # 检查Ctrl键是否按下
            if event.delta > 0:
                self.change_font_size(1)
            else:
                self.change_font_size(-1)
    
    def on_text_configure(self, event):
        # 当文本框大小改变时调整内部布局
        pass
    
    def start_test(self):
        if self.test_running:
            return
            
        try:
            # 获取测试参数
            server_address = self.server_entry.get().strip()
            packet_size = int(self.size_entry.get())
            request_times = int(self.times_entry.get())
            num_threads = int(self.threads_entry.get())
            
            if not server_address.startswith(('http://', 'https://')):
                server_address = 'http://' + server_address
            
            if packet_size <= 0 or request_times <= 0 or num_threads <= 0:
                raise ValueError("All values must be positive")
            
            # 重置测试结果
            self.clear_results()
            self.test_running = True
            self.stop_requested = False
            self.stop_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.DISABLED)
            
            # 初始化进度条
            self.progress['maximum'] = request_times
            self.progress['value'] = 0
            
            # 记录测试开始时间
            self.test_start_time = time.time()
            
            # 在日志中记录测试参数
            self.log_message(f"Starting test with parameters:")
            self.log_message(f"  Server: {server_address}")
            self.log_message(f"  Packet size: {packet_size} bytes")
            self.log_message(f"  Request times: {request_times}")
            self.log_message(f"  Threads: {num_threads}")
            
            # 创建并启动测试线程
            self.test_thread = threading.Thread(
                target=self.run_test,
                args=(server_address, packet_size, request_times, num_threads)
            )
            self.test_thread.daemon = True
            self.test_thread.start()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {str(e)}")
    
    def run_test(self, server_address, packet_size, request_times, num_threads):
        # 重置测试结果
        self.test_results = {
            'successful_requests': 0,
            'failed_requests': 0,
            'total_data': 0,
            'latencies': [],
            'throughputs': []
        }
        
        # 创建线程列表
        threads = []
        requests_per_thread = request_times // num_threads
        remaining_requests = request_times % num_threads
        
        # 创建并启动工作线程
        for i in range(num_threads):
            # 分配请求次数
            thread_requests = requests_per_thread
            if i < remaining_requests:
                thread_requests += 1
                
            thread = threading.Thread(
                target=self.worker_thread,
                args=(server_address, packet_size, thread_requests)
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 测试完成
        self.test_complete()
    
    def worker_thread(self, server_address, packet_size, request_times):
        url = f"{server_address}/size/{packet_size}"
        
        for i in range(request_times):
            if self.stop_requested:
                break
                
            try:
                start_time = time.perf_counter()
                response = requests.get(url, timeout=10)
                end_time = time.perf_counter()
                
                if response.status_code == 200:
                    latency = (end_time - start_time) * 1000  # 转换为毫秒
                    throughput = len(response.content) / (end_time - start_time) / 1024  # KB/s
                    
                    # 更新测试结果（线程安全）
                    with threading.Lock():
                        self.test_results['successful_requests'] += 1
                        self.test_results['total_data'] += len(response.content)
                        self.test_results['latencies'].append(latency)
                        self.test_results['throughputs'].append(throughput)
                        
                        # 更新进度条
                        self.progress['value'] += 1
                        self.root.update()
                        
                    # 记录成功请求
                    self.log_message(f"Request {self.progress['value']}/{self.progress['maximum']} successful - Latency: {latency:.2f} ms, Throughput: {throughput:.2f} KB/s")
                else:
                    with threading.Lock():
                        self.test_results['failed_requests'] += 1
                    self.log_message(f"Request failed with status code {response.status_code}")
                    
            except Exception as e:
                with threading.Lock():
                    self.test_results['failed_requests'] += 1
                self.log_message(f"Request failed: {str(e)}")
    
    def stop_test(self):
        if self.test_running:
            self.stop_requested = True
            self.stop_btn.config(state=tk.DISABLED)
            self.log_message("Test stop requested...")
    
    def test_complete(self):
        self.test_running = False
        self.stop_requested = False
        
        # 计算总测试时间
        total_time = time.time() - self.test_start_time
        
        # 计算统计数据
        avg_latency = statistics.mean(self.test_results['latencies']) if self.test_results['latencies'] else 0
        min_latency = min(self.test_results['latencies']) if self.test_results['latencies'] else 0
        max_latency = max(self.test_results['latencies']) if self.test_results['latencies'] else 0
        
        avg_throughput = statistics.mean(self.test_results['throughputs']) if self.test_results['throughputs'] else 0
        min_throughput = min(self.test_results['throughputs']) if self.test_results['throughputs'] else 0
        max_throughput = max(self.test_results['throughputs']) if self.test_results['throughputs'] else 0
        
        total_data_mb = self.test_results['total_data'] / (1024 * 1024)
        avg_speed = total_data_mb / total_time if total_time > 0 else 0
        
        # 更新结果文本
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "=== Test Results ===\n\n")
        self.results_text.insert(tk.END, f"Successful Requests: {self.test_results['successful_requests']}\n")
        self.results_text.insert(tk.END, f"Failed Requests: {self.test_results['failed_requests']}\n")
        self.results_text.insert(tk.END, f"Total Data Transferred: {total_data_mb:.2f} MB\n")
        self.results_text.insert(tk.END, f"Total Time: {total_time:.2f} seconds\n")
        self.results_text.insert(tk.END, f"Average Speed: {avg_speed:.2f} MB/s\n\n")
        self.results_text.insert(tk.END, "=== Latency (ms) ===\n")
        self.results_text.insert(tk.END, f"Average: {avg_latency:.2f}\n")
        self.results_text.insert(tk.END, f"Minimum: {min_latency:.2f}\n")
        self.results_text.insert(tk.END, f"Maximum: {max_latency:.2f}\n\n")
        self.results_text.insert(tk.END, "=== Throughput (KB/s) ===\n")
        self.results_text.insert(tk.END, f"Average: {avg_throughput:.2f}\n")
        self.results_text.insert(tk.END, f"Minimum: {min_throughput:.2f}\n")
        self.results_text.insert(tk.END, f"Maximum: {max_throughput:.2f}\n")
        self.results_text.config(state=tk.DISABLED)
        
        # 更新图表
        self.update_charts()
        
        # 更新按钮状态
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 记录测试完成
        self.log_message(f"Test completed in {total_time:.2f} seconds")
    
    def update_charts(self):
        # 清除旧图表
        self.ax1.clear()
        self.ax2.clear()
        
        # 绘制延迟图表
        if self.test_results['latencies']:
            self.ax1.plot(self.test_results['latencies'], 'b-', label='Latency (ms)')
            self.ax1.set_title('Request Latency')
            self.ax1.set_xlabel('Request Number')
            self.ax1.set_ylabel('Latency (ms)')
            self.ax1.grid(True)
            self.ax1.legend()
        
        # 绘制吞吐量图表
        if self.test_results['throughputs']:
            self.ax2.plot(self.test_results['throughputs'], 'g-', label='Throughput (KB/s)')
            self.ax2.set_title('Network Throughput')
            self.ax2.set_xlabel('Request Number')
            self.ax2.set_ylabel('Throughput (KB/s)')
            self.ax2.grid(True)
            self.ax2.legend()
        
        # 重绘画布
        self.figure.tight_layout()
        self.canvas.draw()
    
    def clear_results(self):
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)
        
        # 清除图表
        self.ax1.clear()
        self.ax2.clear()
        self.canvas.draw()
        
        # 重置进度条
        self.progress['value'] = 0
        
        # 清除日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkTestClient(root)
    root.mainloop()