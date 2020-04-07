import numpy as np
import multiprocessing
import sys
class Node:
    """docstring for Node"""
    def __init__(self, infoStart):
        self.uid = infoStart.uid
        self.edges = infoStart.edges
        self.queues = infoStart.queues
        self.queue = infoStart.queue
        self.masterQueue = infoStart.masterQueue
        self.SN = "Sleeping"
        self.SE = {}
        for i,j in self.edges:
            self.SE[i] = "Basic"

    def wakeup(self):
        m = self.findMinEdgeAll()
        self.SE[m] = "Branch"
        self.LN = 0
        self.SN = "Found"
        self.findCount = 0
        # send(Connect(0),m)
        self.masterQueue.put(Message("done",[]))
        sys.exit()
    def receiveAndProcess(self):
        while(True):
            message = self.queue.get()
            self.processMessage(message)
    def processMessage(self, message):
        typemessage = message.typemessage
        if typemessage=="wakeup":
            self.wakeup()
        else:
            print("Unrecognised message")

    def findMinEdgeAll(self):
        return self.edges[0][0]


class InfoStart:
    """docstring for InfoStart"""
    def __init__(self, uid, edges, queues, queue, masterQueue):
        self.uid = uid
        self.edges = edges
        self.queues = queues
        self.queue = queue
        self.masterQueue = masterQueue
def nodecode(infoStart):
    node = Node(infoStart)
    node.receiveAndProcess()


class Message():
    """docstring for Message"""
    def __init__(self, typemessage, metadata):
        self.typemessage = typemessage
        self.metadata = metadata

        

        
if __name__ == '__main__':
    testNodes = [0,1,2]
    testEdges = [(0,1,1),(1,2,2),(2,0,3)]
    numNodes = len(testNodes)
    adjacencyMatrix = np.zeros((numNodes,numNodes))
    for i,j,k in testEdges:
        adjacencyMatrix[i][j] = k
        adjacencyMatrix[j][i] = k
    adjacencyList = [[] for i in range(numNodes)]
    for i in range(numNodes):
        for j in range(numNodes):
            if(adjacencyMatrix[i][j]!=0):
                adjacencyList[i].append((j,adjacencyMatrix[i][j]))
    nodesQueues = [multiprocessing.Queue() for i in range(numNodes)]
    masterQueue = multiprocessing.Queue()
    processes = []
    for i in range(numNodes):
        infoStart = InfoStart(i, adjacencyList[i], [nodesQueues[j] for j,k in adjacencyList[i]], nodesQueues[i], masterQueue)
        p = multiprocessing.Process(target=nodecode, args=(infoStart,))
        p.start()
        processes.append(p)
    nodesQueues[0].put(Message("wakeup",[]))
    for i in range(numNodes):
        nodesQueues[i].put(Message("wakeup",[]))
    for i in range(numNodes):
        recvmessage = masterQueue.get()
        print(recvmessage.typemessage, recvmessage.metadata)

