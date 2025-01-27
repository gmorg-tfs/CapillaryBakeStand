import os

class Logger:
    def __init__(self, _base_path, _file_name_base, _file_extension, _header):
        self.base_path = _base_path
        self.file_name_base = _file_name_base
        self.file_name_number = 0
        self.file_extension = _file_extension
        self.header = _header
        self.create_new_file()
    
    def increment_file_number(self):
        self.file_name_number += 1
    
    def get_file_name(self):
        return self.base_path + self.file_name_base + str(self.file_name_number) + self.file_extension
    
    def create_new_file(self):
        while os.path.exists(self.get_file_name()):
            self.increment_file_number()
        self.log(self.header)

    def log(self, data):
        try:
            with open(self.get_file_name(), "a") as f:
                f.write(f"{data}\n")
        except:
            self.create_new_file()
            self.log(data)
