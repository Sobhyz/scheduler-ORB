from random import randint, uniform
import pandas as pd



# 1
# 2
# 3

# "NVIDIA H100", "NVIDIA H100", "NVIDIA H100", 
# "NVIDIA H200", "NVIDIA H200", "NVIDIA H200",
gpus = [
    "NVIDIA H100",
    "NVIDIA H200",
    "NVIDIA A100",
    "NVIDIA A40",
    "NVIDIA A30",
    "NVIDIA A16",
    "NVIDIA L40",
    "NVIDIA L40S",
    "NVIDIA L4",
    "NVIDIA T4",
    "NVIDIA V100",
    "NVIDIA P100",
    "NVIDIA P40",
    "NVIDIA P4",
    "NVIDIA RTX 6000 Ada",
    "NVIDIA RTX 5000 Ada",
    "NVIDIA RTX 4500 Ada",
    "NVIDIA RTX 4000 Ada",
    "NVIDIA GeForce RTX 5090",
    "NVIDIA GeForce RTX 5080",
    "NVIDIA GeForce RTX 5070 Ti",
    "NVIDIA GeForce RTX 5070",
    "NVIDIA GeForce RTX 4090",
    "NVIDIA GeForce RTX 4080 SUPER",
    "NVIDIA GeForce RTX 4080",
    "NVIDIA GeForce RTX 4070 Ti SUPER",
    "NVIDIA GeForce RTX 4070 Ti",
    "NVIDIA GeForce RTX 4070 SUPER",
    "NVIDIA GeForce RTX 4070",
    "NVIDIA GeForce RTX 4060 Ti",
    "NVIDIA GeForce RTX 4060",
    "NVIDIA GeForce RTX 3090 Ti",
    "NVIDIA GeForce RTX 3090",
    "NVIDIA GeForce RTX 3080 Ti",
    "NVIDIA GeForce RTX 3080",
    "NVIDIA GeForce RTX 3070 Ti",
    "NVIDIA GeForce RTX 3070",
    "AMD Radeon RX 7900 XTX",
    "AMD Radeon RX 7900 XT",
    "AMD Radeon RX 7900 GRE",
    "AMD Radeon RX 7800 XT",
    "AMD Radeon RX 7700 XT",
    "AMD Radeon RX 6950 XT",
    "AMD Radeon RX 6900 XT",
    "AMD Radeon RX 6800 XT",
    "AMD Radeon RX 6800",
    "Intel Arc A770",
    "Intel Arc A750",
    "Intel Arc B770",
    "Intel Arc B750"
]

dataSetSize = 10000



numbersList = []
gpusList = []
timeList = []
TOR = []
MEM = []

for _ in range(dataSetSize):
    gpuIdx = randint(0, len(gpus)-1)
    time = randint(1, 15)
    numberOfGpus = randint(1, 8)
    tor = uniform(0,5000)
    mem = randint(1, 2048)

    numbersList.append(numberOfGpus)
    gpusList.append(gpus[gpuIdx])
    timeList.append(time)
    TOR.append(tor)
    MEM.append(mem)

dataSet = pd.DataFrame({'count':numbersList,'device':gpusList,'time':timeList, "TOR": TOR, "MEM": MEM})
dataSet.to_csv('devicesDataSet.csv', index=False)

