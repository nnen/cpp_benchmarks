import sys
import os
from os import path
import tkinter as tk
from tkinter import ttk
import logging
import subprocess
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
        if len(self.children) == 1:
            child = self.children[0]
            self.name = f"{self.name}/{child.name}"
            self.children = child.children
            self.children_by_name = child.children_by_name
            for child in self.children:
                child.parent = self
            self.reduce()
        
        for child in self.children:
            child.reduce()


class BenchmarkInfo:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.tests = BenchmarkTestInfo(self.name, None, self)
    
    def add_test(self, test_name: list[str]):
        return self.tests.get_or_create_test(test_name)
    
    def discover_tests(self):
        proc = subprocess.Popen([self.path, "--benchmark_list_tests"], stdout=subprocess.PIPE)
        for line in proc.stdout:
            line = line.decode("utf-8").strip()
            if len(line) > 0:
                parts = line.split("/")
                self.add_test(parts)
                LOGGER.info(f"Discovered test '{line}' for benchmark '{self.name}'")
        self.tests.reduce()


class Runner:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.benchmarks = []  # type: list[BenchmarkInfo]
    
    def discover(self):
        bin_dir = path.join(self.root_dir, "out", "build", "x64-Release")
        LOGGER.info(f"Scanning directory '{bin_dir}'...")
        for dir_name in os.listdir(bin_dir):
            benchmark_dir = path.join(bin_dir, dir_name)
            LOGGER.info(f"Scanning directory '{benchmark_dir}'...")
            if not path.isdir(benchmark_dir):
                continue
            for file_name in os.listdir(benchmark_dir):
                if not file_name.endswith(".exe"):
                    continue
                benchmark_name = file_name[:-4]
                file_path = path.join(benchmark_dir, file_name)
                if not path.isfile(file_path):
                    continue
                benchmark_info = BenchmarkInfo(benchmark_name, file_path)
                self.benchmarks.append(benchmark_info)
                try:
                    benchmark_info.discover_tests()
                except Exception as e:
                    LOGGER.exception(e)
                LOGGER.info(f"Discovered benchmark '{benchmark_name}', path '{file_path}'")
            #if name.endswith(".exe"):
            #    name = name[:-4]
            #    benchmark = BenchmarkInfo(name, path.join(bin_dir, name + ".exe"))
            #    self.benchmarks.append(benchmark)
            #    benchmark.tests = self.discover_tests(benchmark)
    

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
    
    def _create_items(self, test: BenchmarkTestInfo, parent: str):
        self.insert(parent, "end", test.qualified_name, text=test.name)
        for child in test.children:
            self._create_items(child, test.qualified_name)


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
    
    def append_line(self, line: str):
        self.text.insert(tk.END, line + "\n")
        self.text.see(tk.END)


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("C++ Benchmark Runner")
        self.geometry("600x800")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)

        lbl1 = tk.Label(self, text="Benchmarks")
        lbl1.grid(row=0, column=0, sticky=tk.W, pady=2)

        self.benchmarks = tk.Listbox(self)
        self.benchmarks.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)
        self.benchmarks.bind("<<ListboxSelect>>", self.on_benchmark_selected)

        lbl2 = tk.Label(self, text="Benchmark Tests")
        lbl2.grid(row=0, column=1, sticky=tk.W, pady=2)

        self.benchmark_tests = BenchmarkTestList(self)
        self.benchmark_tests.grid(row=1, column=1, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)

        output_lbl = tk.Label(self, text="Output")
        output_lbl.grid(row=0, column=2, sticky=tk.W, pady=2)

        self.output_panel = OutputPanel(self)
        self.output_panel.grid(row=1, column=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=2)

        button_frame = tk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S)

        self.run_button = tk.Button(button_frame, text="Run", command=self.run_benchmarks)
        self.run_button.pack(side=tk.RIGHT)

        self.runner = Runner(path.dirname(__file__))
        self.runner.discover()
        for benchmark in self.runner.benchmarks:
            self.benchmarks.insert(tk.END, benchmark.name)
    
    def on_benchmark_selected(self, event):
        selection = self.benchmarks.curselection()
        if len(selection) == 0:
            return
        index = int(selection[0])
        benchmark = self.runner.benchmarks[index]

        self.benchmark_tests.set_benchmark(benchmark)

    def run_benchmarks(self):
        pass


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
