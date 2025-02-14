import numpy as np
import matplotlib.pyplot as plt




file_path = "C:\\data\\toaster\\toaster_data_10.csv"

#data = np.genfromtxt(file_path, delimiter=',', skip_header=1, usecols=(0, 1, 2))
data = np.genfromtxt(file_path, delimiter=',', skip_header=1)
time = data[:, 0]
pressure = data[:, 1]
temperature = data[:, 2]
masses = np.arange(1, 76)
rga = data[:, 3:79]

#rga mass 1 is column 0
#rga values for mas n is column n-1
water_17 = rga[:, 16]
water_18 = rga[:, 17]
water_19 = rga[:, 18]

water = water_17 + water_18 + water_19



fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
import time as t
start = t.time()
ax1.plot(time, temperature, c='r')
ax2.semilogy(time, pressure)
plt.xticks([time[0], time[-1]])
end = t.time()
print("Time to plot: ", end - start)
plt.figure()
a= np.array([])
for i in range(1, len(time)):
    dt = time[i] - time[i-1]
    a = np.append(a, [dt])
plt.plot(a)
plt.figure()
plt.plot(time, water)

plt.show()