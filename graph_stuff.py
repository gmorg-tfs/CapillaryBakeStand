import numpy as np
import matplotlib.pyplot as plt
import glob
import argparse

#file_path = "C:\\data\\toaster\\toaster_data_24.csv"
#file_path = "C:\\Data\\toaster\\2025_03_24_toaster_data_2.csv"

def get_most_recent_data_file(base_path):
    files = glob.glob(base_path + "2*.csv") #good for the next ~1000 years
    return files[-1]


def load_data_from_file(path):
    data = np.genfromtxt(path, delimiter=',', skip_header=1)
    time = data[:, 0]
    pressure = data[:, 1]
    temperature = data[:, 2]
    masses = np.arange(1, 76)
    rga = data[:, 3:79]
    return time, pressure, temperature, masses, rga

#file_path = "C:\\Data\\toaster\\2025_03_13_toaster_data_1.csv"

def plot_rga_mass_range(masses, rga, time):
    data = np.zeros(len(rga))
    for m in masses:
        for i in range(len(data)-1):
            data[i] += rga[i, m-1]
    plt.plot(time, data, ".")


def plot_temperature_pressure(time, temperature, pressure):
    fig, ax1 = plt.subplots()
    ax1.plot(time, temperature, "r")
    ax1.set_ylabel("Temperature (C)", color="r")
    ax2 = ax1.twinx()
    ax2.plot(time, pressure, "b")
    ax2.set_ylabel("Pressure (mbar)", color="b")
    plt.xlabel("Time (min)")

def main(file_path=None):
    if not file_path:
        file_path = get_most_recent_data_file("C:\\data\\toaster\\")
    time, pressure, temperature, masses, rga = load_data_from_file(file_path)
    time = (time - time[0])/60

    plot_rga_mass_range([3,4,5], rga, time)
    plot_rga_mass_range([17, 18, 19], rga, time)
    plot_rga_mass_range([27, 28, 29], rga, time)
    plot_rga_mass_range([31,32,33], rga, time)
    plot_rga_mass_range([43,44,45], rga, time)
    plt.legend(["He", "H2O", "N2", "O2", "CO2"])
    plt.xlabel("Time (min)")
    plt.ylabel("%")
    plot_temperature_pressure(time, temperature, pressure)

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot toaster data")
    parser.add_argument("--file", "-f", dest="file_path", help="Path to CSV file to plot")
    args = parser.parse_args()
    main(args.file_path)


#rga mass 1 is column 0
#rga values for mas n is column n-1
#water_17 = rga[:, 16]
#water_18 = rga[:, 17]
#water_19 = rga[:, 18]

#water = water_17 + water_18 + water_19