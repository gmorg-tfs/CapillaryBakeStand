import numpy as np
import matplotlib.pyplot as plt

file_path = "C:\\data\\toaster\\toaster_data_9.csv"
#file_path = "C:\\Users\\robertjaspe.spafford\\Downloads\\toaster_data_24(toaster_data_24).csv"

data = np.genfromtxt(file_path, delimiter=',', skip_header=1, usecols=(0, 2, 3))

time, temp, pressure = data.T


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