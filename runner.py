import sys
import os
import io
import json
from os import path
import tkinter as tk
from tkinter import ttk
import logging
import subprocess
import threading
import queue
from typing import Optional


LOGGER = logging.getLogger(__name__)


class BenchmarkTestInfo:
    def __init__(self, name: str, parent: Optional['BenchmarkTestInfo'] = None, benchmark: Optional["BenchmarkInfo"] = None):
        self.name = name
        self.benchmark = benchmark
        self.selected = False

        self.qualified_name = name
        if parent is not None:
            self.qualified_name = f"{parent.qualified_name}/{name}"

        self.parent = parent  # type: Optional[BenchmarkTestInfo]
        self.children = []  # type: list[BenchmarkTestInfo]
        self.children_by_name = {}  # type: dict[str, BenchmarkTestInfo]
    
    def __str__(self):
        return self.name
    
    def __iter__(self):
        return iter(self.children)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def get_or_create_test(self, test_name: list[str]):
        if len(test_name) == 0:
            return self
        try:
            child = self.children_by_name[test_name[0]]
        except KeyError:
            child = BenchmarkTestInfo(test_name[0], self, self.benchmark)
            self.children.append(child)
            self.children_by_name[child.name] = child
        return child.get_or_create_test(test_name[1:])
    
    def reduce(self):
        for child in self.children:
            child.reduce()
        
        if len(self.children) == 1:
            child = self.children[0]
            self.name = f"{self.name}/{child.name}"
            self.children = child.children
            self.children_by_name = child.children_by_name
            for child in self.children:
                child.parent = self
            self.reduce()


class BenchmarkInfo:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.tests = BenchmarkTestInfo(self.name, None, self)
    
    def add_test(self, test_name: list[str]):
        return self.tests.get_or_create_test(test_name)
    
    def discover_tests(self):
        proc = subprocess.Popen([self.path, "--benchmark_list_tests"], stdout=subprocess.PIPE)
        count = 0
        for line in proc.stdout:
            line = line.decode("utf-8").strip()
            if len(line) > 0:
                parts = line.split("/")
                self.add_test(parts)
                count += 1
                LOGGER.info(f"Discovered test '{line}' for benchmark '{self.name}'")
        for test in self.tests:
            test.reduce()
        return count > 0


class BenchmarkTestResults:
    def __init__(self, benchmark_name: str, json: Optional[dict] = None):
        assert benchmark_name is not None

        self.json = json
        self.name = json["name"]
        self.qualified_name = f"{benchmark_name}/{self.name}"
        self.cpu_time = json["cpu_time"]
        self.real_time = json["real_time"]
        self.time_unit = json["time_unit"]
        self.iterations = json["iterations"]


class BenchmarkResults:
    def __init__(self, name: str, json: Optional[dict] = None):
        assert name is not None

        self.json = json
        self.benchmark_name = name  # type: Optional[str]
        self.tests = []  # type: list[BenchmarkTestResults]

        if self.json is not None:
            self._parse_json(self.json)
    
    def _parse_json(self, json: dict):
        #self.benchmark_name = json.get("name")
        tests = json.get("benchmarks", None)
        if tests is not None:
            for test_json in tests:
                self.tests.append(BenchmarkTestResults(self.benchmark_name, test_json))


class Message:
    pass


class BenchmarkMessage(Message):
    def __init__(self, test: BenchmarkTestInfo):
        self.test = test


class OutputMessage(Message):
    def __init__(self, line: str):
        super().__init__()
        self.line = line


class FinishedMessage(Message):
    def __init__(self, return_code: int, result: Optional[BenchmarkResults]):
        super().__init__()
        self.return_code = return_code
        self.result = result


class Runner:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.benchmarks = []  # type: list[BenchmarkInfo]
        self.selected_benchmark = None  # type: Optional[BenchmarkInfo]

        self.is_running = False  # type: bool
        self._thread = None  # type: Optional[threading.Thread]
        self._process = None  # type: Optional[subprocess.Popen]
        self._command_queue = queue.Queue(8)
        self._output_queue = queue.Queue(1024)
        self._output_buffer = io.StringIO()

    def start(self):
        if (self._thread is not None) and (not self._thread.is_alive):
            self._thread = None
        if self._thread is None:
            self._thread = threading.Thread(target=self._background_worker)
            self._thread.start()
        self._command_queue.put(("start", ))
    
    def stop(self):
        self._command_queue.put(("stop", ))
    
    def update(self, output_callback=None, event_callback=None):
        while True:
            try:
                event = self._output_queue.get_nowait()
                if event_callback is not None:
                    event_callback(event)
                if output_callback is not None:
                    if isinstance(event, OutputMessage):
                        output_callback(event.line)
            except queue.Empty:
                break
    
    def _background_worker(self):
        while True:
            try:
                try:
                    command = self._command_queue.get_nowait()
                    if command[0] == "start":
                        self._start_process()
                    elif command[0] == "stop":
                        self._kill_process()
                    continue
                except queue.Empty:
                    pass
            
                if self._process is not None:
                    line = self._process.stdout.readline()
                    line = line.decode("utf-8")
                    if len(line) == 0:
                        self._finish_benchmark()
                    else:
                        self._output_buffer.write(line)
                        self._output_queue.put(OutputMessage(line=line))
                    continue
            except Exception as e:
                LOGGER.exception(e)
    
    def _start_process(self):
        if self._process is not None:
            return False
        self._output_buffer = io.StringIO()
        self._process = subprocess.Popen(
            [self.selected_benchmark.path, "--benchmark_format=json" ], 
            stdout=subprocess.PIPE
        )
        self.is_running = True
        return True
    
    def _kill_process(self):
        if self._process is None:
            return False
        self._process.kill()
        return True
    
    def _finish_benchmark(self):
        assert self._process is not None
        return_code = self._process.wait()
        self._process = None
        self.is_running = False

        result = None
        if return_code == 0:
            try:
                raw_json = self._output_buffer.getvalue()
                result_json = json.loads(raw_json)
                result = BenchmarkResults(self.selected_benchmark.name, result_json)
            except Exception as e:
                LOGGER.exception(e)
        self._output_queue.put(FinishedMessage(return_code=return_code, result=result))

    def _scan_directory(self, dir_path: str):
        for file_name in os.listdir(dir_path):
            if file_name.startswith("."):
                continue
            file_path = path.join(dir_path, file_name)
            if path.isfile(file_path) and file_name.endswith(".exe"):
                try:
                    basename = file_name[:-4]
                    info = BenchmarkInfo(basename, file_path)
                    if info.discover_tests():
                        self.benchmarks.append(info)
                        LOGGER.info(f"Discovered benchmark '{info.name}' at path '{file_path}'.")
                except Exception as e:
                    LOGGER.exception(e)
            elif path.isdir(file_path):
                self._scan_directory(file_path)
    
    def discover(self):
        self._scan_directory(self.root_dir)


class BenchmarkTestList(ttk.Treeview):
    def __init__(self, parent, benchmark: BenchmarkInfo|None = None):
        super().__init__(parent, columns=("time", "cpu", "iterations"))
        self.benchmark = benchmark

        self.heading("#0", text="Test Name")
        self.heading("time", text="Real Time")
        self.heading("cpu", text="CPU Time")
        self.heading("iterations", text="Iterations")

    def set_benchmark(self, benchmark: BenchmarkInfo):
        self.delete(*self.get_children())
        self.benchmark = benchmark
        if self.benchmark is not None:
            for test in self.benchmark.tests:
                self._create_items(test, "")
    
    def set_test_result(self, result: BenchmarkTestResults):
        self.item(result.qualified_name, values=[result.real_time, result.cpu_time, result.iterations])
    
    def _create_items(self, test: BenchmarkTestInfo, parent: str):
        self.insert(parent, "end", test.qualified_name, text=test.name, open=True)
        for child in test.children:
            self._create_items(child, test.qualified_name)


class TestSelectionPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.selected_tests = set()  # type: set[string]

        self.list = tk.Listbox(self)
        self.list.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.clear_button = tk.Button(button_frame, text="Clear", command=self.clear)
        self.clear_button.pack(side=tk.RIGHT)
    
    def clear(self):
        self.selected_tests.clear()
        self.list.delete(0, tk.END)
    
    def add_test(self, test_name: str):
        if test_name is self.selected_tests:
            return
        self.list.insert(tk.END, test_name)
        self.selected_tests.add(test_name)
    
    def remove_test(self, test_name: str):
        if test_name not in self.selected_tests:
            return
        items = self.list.get(0, tk.END)  # type: list[str]
        index = items.index(test_name)
        if index >= 0:
            self.list.delete(index)
            self.selected_tests.remove(test_name)
    
    def toggle_test(self, test_name: str):
        if test_name in self.selected_tests:
            self.remove_test(test_name)
        else:
            self.add_test(test_name)


class OutputPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.text = tk.Text(self)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text.insert(tk.END, "Output...")

        self.vscrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text.config(yscrollcommand=self.vscrollbar.set)
    
    def clear(self):
        self.text.delete(1.0, tk.END)

    def append(self, value: str):
        self.text.insert(tk.END, value)
        self.text.see(tk.END)
    
    def append_line(self, line: str):
        self.append(line + "\n")


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("C++ Benchmark Runner")
        self.geometry("600x800")
        #self.grid_columnconfigure(0, weight=1)
        #self.grid_columnconfigure(1, weight=1)
        #self.grid_columnconfigure(2, weight=1)
        #self.grid_rowconfigure(1, weight=1)

        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        #main_pane.grid(row=0, column=0, rowspan=2, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S)

        #pw = ttk.PanedWindow(main_pane, orient=tk.HORIZONTAL)

        pane1 = tk.Frame(main_pane)
        main_pane.add(pane1)
        #pane1.pack(side=tk.LEFT, fill=tk.Y)
        #pw.add(pane1)
        #pane1.grid(row=0, column=0, rowspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)

        lbl1 = tk.Label(pane1, text="Benchmarks")
        lbl1.pack(side=tk.TOP, anchor=tk.W)

        self.benchmarks = tk.Listbox(pane1)
        self.benchmarks.pack(side=tk.TOP, fill=tk.X)
        self.benchmarks.bind("<<ListboxSelect>>", self.on_benchmark_selected)

        lbl2 = tk.Label(pane1, text="Benchmark Tests")
        lbl2.pack(side=tk.TOP, anchor=tk.W)

        self.benchmark_tests = BenchmarkTestList(pane1)
        self.benchmark_tests.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        self.benchmark_tests.bind("<Double-1>", self._on_test_double_clicked)

        selection_pane = tk.Frame(main_pane)
        main_pane.add(selection_pane)
        #selection_pane.pack(side=tk.LEFT, fill=tk.Y)
        #pw.add(selection_pane)
        #selection_pane.grid(row=0, column=1, rowspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)

        selection_lbl = tk.Label(selection_pane, text="Selected tests")
        selection_lbl.pack(side=tk.TOP, anchor=tk.W)

        self.selection_panel = TestSelectionPanel(selection_pane)
        self.selection_panel.pack(side=tk.TOP, expand=True, fill=tk.BOTH)

        output_pane = tk.Frame(main_pane)
        main_pane.add(output_pane)
        #output_pane.pack(side=tk.LEFT, fill=tk.Y)
        #pw.add(output_pane)
        #output_pane.grid(row=0, column=2, rowspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)

        output_lbl = tk.Label(output_pane, text="Output")
        output_lbl.pack(side=tk.TOP, anchor=tk.W)

        self.output_panel = OutputPanel(output_pane)
        self.output_panel.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        
        button_frame = tk.Frame(self)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        #button_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S)

        self.status_label = tk.Label(button_frame, text="Status")
        self.status_label.pack(side=tk.LEFT)

        self.run_button = tk.Button(button_frame, text="Run", command=self.run_benchmarks)
        self.run_button.pack(side=tk.RIGHT)

        self.runner = Runner(path.dirname(__file__))
        self.runner.discover()
        for benchmark in self.runner.benchmarks:
            self.benchmarks.insert(tk.END, benchmark.name)
        
        self.after(1000, self._update_runner)

    def _update_runner(self):
        self.after(500, self._update_runner)
        if self.runner.is_running:
            self.status_label.config(text="Running...")
        else:
            self.status_label.config(text="Idle")
        self.runner.update(event_callback=self._on_runner_event)
    
    def _on_runner_event(self, event: Message):
        if isinstance(event, OutputMessage):
            self.output_panel.append(event.line)
        elif isinstance(event, FinishedMessage):
            if event.result is not None:
                for test in event.result.tests:
                    self.benchmark_tests.set_test_result(test)
    
    def on_benchmark_selected(self, event):
        selection = self.benchmarks.curselection()
        if len(selection) == 0:
            return
        index = int(selection[0])
        benchmark = self.runner.benchmarks[index]

        self.benchmark_tests.set_benchmark(benchmark)
        self.runner.selected_benchmark = benchmark
    
    def _on_test_double_clicked(self, event):
        item = self.benchmark_tests.selection()[0]
        self._select_tree_item(item)
        #self.selection_panel.toggle_test(item)
    
    def _select_tree_item(self, item_id: str):
        children = self.benchmark_tests.get_children(item_id)
        if (children is not None) and (len(children) > 0):
            for child in children:
                self._select_tree_item(child)
        else:
            self.selection_panel.add_test(item_id)
    
    def run_benchmarks(self):
        self.output_panel.clear()
        self.runner.start()


class ResultsWindow(tk.Toplevel):
    def __init__(self, parent, benchmark_name, test_name):
        super().__init__(parent)
        self.title(f"Results for '{benchmark_name}'")
        self.geometry("400x200")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        lbl1 = tk.Label(self, text="Results")
        lbl1.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.results = tk.Text(self)
        self.results.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)
        self.results.insert(tk.END, "Hello, world!")


def main():
    logging.basicConfig(level=logging.INFO)

    window = MainWindow()
    window.mainloop()


if __name__ == "__main__":
    root_dir = path.dirname(__file__)
    print(f"ROOT DIR: {root_dir}")
    main()
