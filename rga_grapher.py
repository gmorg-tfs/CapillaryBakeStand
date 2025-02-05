import numpy as np
import matplotlib.pyplot as plt


file_path = "C:\\data\\toaster\\toaster_rga_data_51.csv"

temp = np.array([])
pressure = np.array([])
time = np.array([])

with open(file_path, "r") as file:
    for this_line in file.readlines():
        try:
            line = this_line.split(",")
            time_column = 0
            pressure_column = 1
            temperature_column = 2
            temp = np.append(temp, [float(line[temperature_column])])
            time = np.append(time, [float(line[time_column])])
            pressure = np.append(pressure, [float(line[pressure_column])])
        except:
            pass

fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
ax1.plot(time, temp, c='r')
ax2.semilogy(time, pressure)
plt.xticks([time[0], time[-1]])
plt.figure()
a= np.array([])
for i in range(1, len(time)):
    dt = time[i] - time[i-1]
    a = np.append(a, [dt])
plt.plot(a)
plt.show()