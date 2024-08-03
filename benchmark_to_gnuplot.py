import sys
import argparse
import json
import pprint


class Data:
    def __init__(self):
        self._x_axis = []  # type: list[float]
        self._data_set_names = []  # type: list[str]
        self._data = {}  # type: dict[float, dict[str, float]]
    
    def add_x_value(self, x_value: float):
        self._x_axis.append(x_value)
    
    def add_datapoint(self, data_set_name: str, x_value: float, value: float):
        self.add_data_set(data_set_name)
        self.add_x_value(x_value)
        try:
            data = self._data[x_value]
        except KeyError:
            data = {}
            self._data[x_value] = data
        data[data_set_name] = value

    def add_data_set(self, data_set_name: str):
        if data_set_name not in self._data_set_names:
            self._data_set_names.append(data_set_name)
    
    def write(self, out):
        w = out.write

        x_axis = sorted(set(self._x_axis))

        for data_set_name in self._data_set_names:
            w("\t")
            w(data_set_name)
        
        for x_value in x_axis:
            data = self._data[x_value]
            w("\n")
            w(str(x_value))
            for data_set_name in self._data_set_names:
                w("\t")
                try:
                    w(f"{data[data_set_name]:.6f}")
                    #w(str(data[data_set_name]))
                except KeyError:
                    w("0")


def convert_json_file(json_file_path: str):
    data = Data()
    with open(json_file_path, 'r') as f:
        json_data = json.load(f)
        benchmarks = json_data['benchmarks']
        for benchmark in benchmarks:
            name = benchmark['name']
            parts = name.split("/")
            x_value = int(parts[1])
            real_time = benchmark['real_time']
            data.add_datapoint(parts[0], x_value, real_time)
    data.write(sys.stdout)
    sys.stdout.write("\n\n")


def main():
    print(repr(sys.argv))
    for arg in sys.argv[1:]:
        convert_json_file(arg)


if __name__ == '__main__':
    main()

