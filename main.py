import numpy as np
import multiprocessing
import sys
class Node:
    """docstring for Node"""
    def __init__(self, infoStart):
        self.uid = infoStart.uid
        self.edges = infoStart.edges
        self.edgeToWeight = {}
        for i,j in self.edges:
            self.edgeToWeight[i] = j
        self.queues = infoStart.queues
        self.queue = infoStart.queue
        self.masterQueue = infoStart.masterQueue
        self.SN = "Sleeping"
        self.SE = {}
        for i,j in self.edges:
            self.SE[i] = "Basic"

    def wakeup(self):
        m = self.findMinEdge()
        self.SE[m] = "Branch"
        self.LN = 0
        self.SN = "Found"
        self.findCount = 0
        self.queues[m].put(Message("connect",[0], self.uid))
        # self.masterQueue.put(Message("done",[], self.uid)) #just for seeing if code works
        # sys.exit() #just for seeing if code works
    def receiveAndProcess(self):
        while(True):
            message = self.queue.get()
            self.processMessage(message)
    def processMessage(self, message):
        typemessage = message.typemessage
        senderid = message.senderid
        metadata = message.metadata
        if typemessage=="wakeup":
            self.wakeup()
        elif typemessage=="connect":
            self.connect(metadata[0], senderid, message)
        elif typemessage=="initiate":
            self.initiate(metadata[0], metadata[1], metadata[2], senderid)
        elif typemessage=="test":
            self.testResponse(metadata[0], metadata[1], senderid, message)
        elif typemessage=="accept":
            self.accept(senderid)
        elif typemessage=="reject":
            self.reject(senderid)
        elif typemessage=="report":
            self.reportResponse(metadata[0], senderid, message)
        elif typemessage=="changeRoot":
            self.changeRootResponse()
        else:
            print("Unrecognised message")

    def findMinEdge(self):
        minEdge = self.edges[0][0]
        minEdgeWeight = self.edges[0][1]
        for i,j in self.edges:
            if j<minEdgeWeight:
                minEdge = i
                minEdgeWeight = j
        return minEdge

    def connect(self, level, senderEdge, message):
        if(self.SN=="Sleeping"):
            self.wakeup()
        if(level<self.LN):
            self.SE[senderEdge] = "Branch"
            self.queues[senderEdge].put(Message("initiate", [self.LN, self.FN, self.SN], self.uid))
            if self.SN== "Find":
                self.findCount +=1
        elif(self.SE[senderEdge]=="Basic"):
            self.queue.put(message)
        else:
            self.queues[senderEdge].put(Message("initiate", [self.LN+1, self.edgeToWeight[senderEdge], "Find"], self.uid))

    def initiate(self, level, fid, status, senderEdge):
        self.LN = level
        self.FN = fid
        self.SN = status
        self.inBranch = senderEdge
        self.bestEdge = None
        self.bestWeight = float('inf')
        for i,_ in self.edges:
            if i==senderEdge:
                continue
            if self.SE[i]!="Branch":
                continue
            self.queues[i].put(Message("initiate", [level, fid, status], self.uid))
            if status=="Find":
                self.findCount+=1
        if status=="Find":
            self.test()

    def test(self):
        havebasic = False
        for i,j in self.edges:
            if self.SE[i]=="Basic":
                havebasic=True
                m = self.findMinBasicEdge()
                self.test_edge = m
                self.queues[m].put(Message("test",[self.LN, self.FN], self.uid))
                break
        if(not havebasic):
            self.test_edge = None
            self.report()

    def findMinBasicEdge(self):
        minEdge = -1
        minEdgeWeight = float('inf')
        for i, j in self.edges:
            if j < minEdgeWeight and self.SE[i]=="Basic":
                minEdge = i
                minEdgeWeight = j
        return minEdge


    def testResponse(self, level, fid, senderEdge, message):
        if self.SN=="Sleeping":
            self.wakeup()
        if level>self.LN:
            self.queue.put(message)
        elif self.FN != fid:
            self.queues[senderEdge].put(Message("accept", [], self.uid))
        else:
            if self.SE[senderEdge] == "Basic":
                self.SE[senderEdge] = "Rejected"
            if (self.test_edge is None or self.test_edge != senderEdge):
                self.queues[senderEdge].put(Message("reject", [], self.uid))
            else:
                self.test()

    def accept(self, senderEdge):
        self.test_edge = None
        if self.edgeToWeight[senderEdge]<self.bestWeight:
            self.bestEdge = senderEdge
            self.bestWeight = self.edgeToWeight[senderEdge]
        self.report()

    def reject(self, senderEdge):
        if self.SE[senderEdge] == "Basic":
            self.SE[senderEdge] = "Rejected"
        self.test()

    def report(self):
        if self.findCount==0 and self.test_edge is None:
            self.SN = "Found"
            self.queues[self.inBranch].put(Message("report", [self.bestWeight], self.uid))

    def reportResponse(self, weightparam, senderEdge, message):
        if senderEdge!=self.inBranch:
            self.findCount-=1
            if weightparam<self.bestWeight:
                self.bestWeight = weightparam
                self.bestEdge = senderEdge
            self.report()
        elif self.SN=="Find":
            self.queue.put(message)
        elif weightparam > self.bestWeight:
            self.changeRoot()
        elif weightparam == self.bestWeight and self.bestWeight == float('inf'):
            self.masterQueue.put(Message("done", [], self.uid))
            sys.exit()

    def changeRoot(self):
        if self.SE[self.bestEdge] == "Branch":
            self.queues[self.bestEdge].put(Message("changeRoot",[],self.uid))
        else:
            self.queues[self.bestEdge].put(Message("connect", [self.LN], self.uid))
            self.SE[self.bestEdge] = "Branch"

    def changeRootResponse(self):
        self.changeRoot()


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
    def __init__(self, typemessage, metadata, senderid):
        self.typemessage = typemessage
        self.metadata = metadata
        self.senderid = senderid

        

        
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
        queuedic = {}
        for j,k in adjacencyList[i]:
            queuedic[j] = nodesQueues[j]
        infoStart = InfoStart(i, adjacencyList[i], queuedic, nodesQueues[i], masterQueue)
        p = multiprocessing.Process(target=nodecode, args=(infoStart,))
        p.start()
        processes.append(p)
    for i in range(numNodes):
        nodesQueues[i].put(Message("wakeup",[], -1))
    for i in range(numNodes):
        recvmessage = masterQueue.get()
        print(recvmessage.typemessage, recvmessage.metadata, recvmessage.senderid)

