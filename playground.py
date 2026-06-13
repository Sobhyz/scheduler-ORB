from multiprocessing import Process, Pool, Lock
from queue import PriorityQueue
from time import sleep

pq = PriorityQueue()

# pq.put((1,3))
# pq.put((1,2))
# pq.put((1,0))
# pq.put((0,1))
pqLock = Lock()
def fun():
    global pq, pqLock

    
    while pq:
        # pq.get()
        with pqLock:
            # print("fun 1")
            if not pq.empty():
                with open("fun1.txt", 'w') as f:
                    f.write("fun1")
                print(pq.get(False),end = "-"*50 + '\n', flush=True)
        # if pq.empty():
        #     pqLock.acquire()
        # else:
        #     pqLock.acquire()


def add():
    from random import randint
    global pq, pqLock
    while True:
        n = randint(1,10)
        # pqLock.acquire()
        with pqLock:
            while n>0:
                with open("fun2.txt", 'w') as f:
                    f.write("fun2")

                a = randint(0,100000)
                b = randint(0,100000)
                print(a,b,end=' ',flush=True)
                pq.put((a,b))
                n-=1
        # pqLock.release()
        sleep(1)

if __name__ == "__main__":
    
    p = Process(target=fun)
    adder = Process(target=add)
    adder.start()
    print("started p1")
    p.start()
    print("started p1")
    
    # p.join()
    # p.join()
    # import os
    # print(os.cpu_count())

