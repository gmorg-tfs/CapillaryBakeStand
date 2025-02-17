import numpy as np
import matplotlib.pyplot as plt


file_path = "C:\\data\\toaster\\toaster_data_24.csv"

def load_data_from_file(path):
    data = np.genfromtxt(path, delimiter=',', skip_header=1)
    time = data[:, 0]
    pressure = data[:, 1]
    temperature = data[:, 2]
    masses = np.arange(1, 76)
    rga = data[:, 3:79]
    return time, pressure, temperature, masses, rga

time, pressure, temperature, masses, rga = load_data_from_file(file_path)


def plot_rga_mass_range(masses, rga, time):
    data = np.zeros(len(rga))
    for m in masses:
        for i in range(len(data)-1):
            data[i] += rga[i, m-1]
    plt.plot(time, data, ".")    



plot_rga_mass_range([17, 18, 19], rga, time)

plt.show()


#rga mass 1 is column 0
#rga values for mas n is column n-1
#water_17 = rga[:, 16]
#water_18 = rga[:, 17]
#water_19 = rga[:, 18]

#water = water_17 + water_18 + water_19