from job import Job
from time import time, sleep
from queue import PriorityQueue
from threading import Thread, Lock
import pandas as pd

# [1,2,3,4] -> [1,2]

class Scheduler:
    totalMemory = 2048
    def __init__(self, jobsToConsider: int=-1, ageLimit: int = 1000):
        self.readyToServe = PriorityQueue()
        self.waitingArea = PriorityQueue()
        self.jobsToConsider = jobsToConsider
        self.ageLimit = ageLimit
        self.generalLock = Lock()
        self.memLock = Lock()
        self.df = pd.read_csv("/Users/Sobhyzz/Desktop/ORB/devicesDataSet.csv")
        

    def recieve_jobs(self) -> None:
        with self.generalLock:
            for _, row in self.df.iterrows():
                tmpJob = Job(row['time'], row['count'], row['MEM'])
                self.waitingArea.put((row['TOR'], tmpJob))

    def move_jobs(self) -> None:

        startTime = time()
        while self.waitingArea:
            with self.generalLock:
                if not self.waitingArea.empty() and \
                (self.readyToServe.qsize() < self.jobsToConsider or self.jobsToConsider==-1):
                    
                    _, currJob = self.waitingArea.get(False)

                    
                    currJob.start_age_modifier()
                    self.readyToServe.put((currJob.calculate_priority(), currJob))
            
                if time() - startTime >= self.ageLimit:
                    self._update_priorites()
                    startTime = time()
                
    def remove_mem(self, val):
        with self.memLock:
            Scheduler.totalMemory -= val

    def add_mem(self, val):
        with self.memLock:
            Scheduler.totalMemory += val

    def serve_jobs(self):
        while self.readyToServe:
            cnt = 0
            with self.generalLock:
                if not self.readyToServe.empty():
                    currJob = self.readyToServe.get(False)[1]
                    if Scheduler.totalMemory >= currJob.memoryRequired:
                        self.remove_mem(currJob.memoryRequired)
                        
                        task = Thread(target=self.process_Job, args=[currJob,])
                        task.start()

                        # 
                        cnt+=1
                        print(Scheduler.totalMemory)
                        
                    else:
                        print(f"served {cnt}")
                        self.readyToServe.put((currJob.calculate_priority(), currJob))
                        cnt = 0

                    # print(f"Serving {currJob.age}")
    
    def process_Job(self, currJob):
        sleep(currJob.timeRequired//10)
        self.add_mem(currJob.memoryRequired)
        currJob.kill_job()
        print("Done")

    

    def _update_priorites(self) -> None:
        tmp = []
        while not self.readyToServe.empty():
            tmp.append(self.readyToServe.get(False)[1])
        
        for entry in tmp:
            self.readyToServe.put((entry.calculate_priority(), entry))

    def main(self):
        self.recieve_jobs()
        mover = Thread(target = self.move_jobs)
        server = Thread(target = self.serve_jobs)

        mover.start()
        server.start()

if __name__ == "__main__":
    sched = Scheduler(jobsToConsider=10)
    sched.recieve_jobs()
    mover = Thread(target = sched.move_jobs)
    server = Thread(target = sched.serve_jobs)

    mover.start()
    server.start()



    



