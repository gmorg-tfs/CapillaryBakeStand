import os

class Logger:
    def __init__(self, _base_path, _file_name_base, _file_extension, _header):
        self.base_path = _base_path
        self.file_name_base = _file_name_base
        self.file_name_number = 0
        self.file_extension = _file_extension
        self.header = _header
        self.buffer = []
        self.max_buffer_size = 10
        self.create_new_file()
    
    def increment_file_number(self):
        self.file_name_number += 1
    
    def get_file_name(self):
        return self.base_path + self.file_name_base + str(self.file_name_number) + self.file_extension
    
    def create_new_file(self):
        while os.path.exists(self.get_file_name()):
            self.increment_file_number()
        with open(self.get_file_name(), "a") as f:
            f.write(f"{self.header}\n")
            if len(self.buffer) > 0:
                for d in self.buffer:
                    f.write(f"{d}\n")
                self.buffer = []

    def log(self, data):
        try:
            with open(self.get_file_name(), "a") as f:
                if len(self.buffer) > 0:
                    for d in self.buffer:
                        f.write(f"{d}\n")
                    self.buffer = []
                f.write(f"{data}\n")
        except:
            if len(self.buffer) > self.max_buffer_size:
                self.create_new_file()
                self.log(data)
            else:
                self.buffer += [data]
