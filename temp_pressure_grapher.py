import numpy as np
import matplotlib.pyplot as plt

file_path = "C:\\data\\toaster\\toaster_data_9.csv"
#file_path = "C:\\Users\\robertjaspe.spafford\\Downloads\\toaster_data_24(toaster_data_24).csv"

temp = np.array([])
pressure = np.array([])
time = np.array([])


with open(file_path, "r") as file:
    lines = file.readlines()
    header = lines[0].split(",")

    time_column = 0
    temperature_column = 2
    pressure_column = 3
    for line in lines[1:]:
        line = line.split(",")
        time = np.append(time, [float(line[time_column])])
        pressure = np.append(pressure, [float(line[pressure_column])])
        temp = np.append(temp, [float(line[temperature_column])])
         

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