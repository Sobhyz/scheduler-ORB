from time import time
from threading import Thread
from uuid import uuid4

class Job:
    def __init__(self, timeRequired: int, numGpus: int, memoryRequired: int) -> None:
        self.age = 0
        self.timeStamp = time()
        self.timeRequired = timeRequired
        self.kill = False
        self.numGpus = numGpus
        self.memoryRequired = memoryRequired
        self.uuid = uuid4()

        # self.ageUpdator = Thread(name = "Age Updator", target=self._update_age)
        
    def __lt__(self, other):
        return self.uuid < other.uuid
    
    
            # print(self.age, self._calculate_priority())

        # print("Killed")

    def calculate_priority(self, timeWeight: float = 0.25, 
                                    numGpusWeight: float = 0.25,
                                    ageWeight: float = 0.25,
                                    memoryWeight: float = 0.25) -> float:

        return timeWeight * self.timeRequired \
            + numGpusWeight * self.numGpus \
            + ageWeight * self.age \
            - memoryWeight * self.memoryRequired
    
    def start_age_modifier(self):
        self.ageUpdator.start()

    def kill_job(self) -> None:
        # print("Relesing resources")
        self.kill = True

