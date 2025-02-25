import numpy as np
import multiprocessing
import sys
import math
DEBUG = False
DEBUGOUTPUT = False
ANALYSIS = False
class Node:
    """docstring for Node"""
    def __init__(self, infoStart):
        self.uid = infoStart.uid #unique identifier
        self.edges = infoStart.edges #list of tuples of the form (nodeId, Weight)
        self.edgeToWeight = {} #a dictionary for the fast retrieval of edgeWeight from NodeId
        for i,j in self.edges:
            self.edgeToWeight[i] = j
        self.queues = infoStart.queues #a dictionary of the messageQueue of the form (nodeId, queue)
        self.queue = infoStart.queue #queue of the self
        self.masterQueue = infoStart.masterQueue #queue of the master process which spawned all processes
        self.SN = "Sleeping" #State of the Node
        self.SE = {} #Dictionary of the form (nodeId, status of edge) used to get the status of edges
        self.test_edge = None 
        for i,j in self.edges:
            self.SE[i] = "Basic"
        if ANALYSIS: self.numMessages = 0

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
            message = self.queue.get() #blocking receive
            self.processMessage(message)
    def processMessage(self, message):
        typemessage = message.typemessage
        senderid = message.senderid
        metadata = message.metadata
        if ANALYSIS: 
            if senderid!=self.uid:
                self.numMessages += 1
        if DEBUG: print("Process ", self.uid, "received ", typemessage, "from " , senderid, "with metadata ", metadata)
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
        elif typemessage=="queryStatus":
            self.queryStatusResponse()
        else:
            if DEBUG: print("Unrecognised message")

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
            if self.SN== "Find" and self.inBranch!=senderEdge:
                self.findCount +=1
        elif(self.SE[senderEdge]=="Basic"):
            self.queue.put(message)
            if ANALYSIS: self.numMessages-=1
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
            if ANALYSIS: self.numMessages-=1
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
        # print("process ", self.uid, "call report")
        if self.findCount==0 and self.test_edge is None:
        # if self.findCount==0 and (not hasattr(self, 'test_edge')):
            # print("process ", self.uid, "entered report", (not hasattr(self, 'test_edge')), self.test_edge)
            self.SN = "Found"
            self.queues[self.inBranch].put(Message("report", [self.bestWeight], self.uid))

    def reportResponse(self, weightparam, senderEdge, message):
        # if DEBUG: print("Process ", self.uid,"report response")
        if senderEdge!=self.inBranch:
            self.findCount-=1
            if weightparam<self.bestWeight:
                self.bestWeight = weightparam
                self.bestEdge = senderEdge
            self.report()
        elif self.SN=="Find":
            self.queue.put(message)
            if ANALYSIS: self.numMessages-=1
        elif weightparam > self.bestWeight:
            self.changeRoot()
        elif weightparam == self.bestWeight and self.bestWeight == float('inf'):
            self.masterQueue.put(Message("done", [self.SE, self.inBranch], self.uid)) #GHS is computed, inform master
            # sys.exit()

    def changeRoot(self):
        if self.SE[self.bestEdge] == "Branch":
            self.queues[self.bestEdge].put(Message("changeRoot",[],self.uid))
        else:
            self.queues[self.bestEdge].put(Message("connect", [self.LN], self.uid))
            self.SE[self.bestEdge] = "Branch"

    def changeRootResponse(self):
        self.changeRoot()

    def queryStatusResponse(self):
        if ANALYSIS:
            self.masterQueue.put(Message("queryAnswer", [self.SE, self.inBranch, self.numMessages-1], self.uid))
        else:
            self.masterQueue.put(Message("queryAnswer", [self.SE, self.inBranch], self.uid))
        sys.exit() #MST computed and sent information to master, time to exit


class InfoStart:
    """docstring for InfoStart"""
    def __init__(self, uid, edges, queues, queue, masterQueue):
        self.uid = uid #Unique id
        self.edges = edges #neighbouring edge and their weights
        self.queues = queues #neighbouring edges queues
        self.queue = queue #nodes own queue
        self.masterQueue = masterQueue #master process queue

def nodecode(infoStart):
    node = Node(infoStart)
    node.receiveAndProcess()


class Message():
    """docstring for Message"""
    def __init__(self, typemessage, metadata, senderid):
        self.typemessage = typemessage #Type of message like wakeup, connect, etc
        self.metadata = metadata #Any extra information bundled up with data
        self.senderid = senderid #Id of whoever sent the message


def readInput(filename):
    f = open(filename, "r")
    lines = f.readlines()
    numNodes = int(lines[0])
    testEdges = [eval(x.rstrip()) for x in lines[1:]]
    return (numNodes, testEdges)


if __name__ == '__main__':
    # testNodes = 3
    # testEdges = [(0,1,1),(1,2,2),(2,0,3)]
    # testNodes = 2
    # testEdges = [(0, 1, 1)]
    numNodes, testEdges = readInput(sys.argv[1])
    adjacencyMatrix = np.zeros((numNodes,numNodes))
    for i,j,k in testEdges:
        adjacencyMatrix[i][j] = k
        adjacencyMatrix[j][i] = k
    numEdgesReal = 0
    for i in range(0, numNodes):
        for j in range(i+1,numNodes):
            if adjacencyMatrix[i][j] !=0:
                numEdgesReal+=1
    adjacencyList = [[] for i in range(numNodes)]
    for i in range(numNodes):
        for j in range(numNodes):
            if(adjacencyMatrix[i][j]!=0):
                adjacencyList[i].append((j,adjacencyMatrix[i][j]))
    nodesQueues = [multiprocessing.Queue() for i in range(numNodes)] #master process has queues of all of the nodes
    masterQueue = multiprocessing.Queue() #master's own queue
    processes = []
    for i in range(numNodes):
        queuedic = {} #node's relevent queue data
        for j,k in adjacencyList[i]:
            queuedic[j] = nodesQueues[j] #only providing neighbouring edges queues
        infoStart = InfoStart(i, adjacencyList[i], queuedic, nodesQueues[i], masterQueue)
        p = multiprocessing.Process(target=nodecode, args=(infoStart,))
        p.start()
        processes.append(p)
    nodesQueues[0].put(Message("wakeup", [], -1))#waking up nodeId 0
    if DEBUG: print("wakeup sent")
    # for i in range(numNodes):
    #     nodesQueues[i].put(Message("wakeup",[], -1))
    # while(True):
    # for i in range(numNodes):
    #     recvmessage = masterQueue.get()
    #     if DEBUG: print(recvmessage.typemessage, recvmessage.metadata, recvmessage.senderid)
    recvmessage = masterQueue.get()
    if recvmessage.typemessage=="done":
        for i in range(numNodes):
            nodesQueues[i].put(Message("queryStatus",[], -1)) #get Branch edges information
    numStatusMessages = 0
    mstAdjacencyMatrix = np.zeros((numNodes,numNodes))
    numTotalMessages = 0
    while(numStatusMessages<numNodes):
        recvmessage = masterQueue.get()
        if recvmessage.typemessage=="queryAnswer":
            # if DEBUG: print("Got status")
            if DEBUG: print("Got status", recvmessage.typemessage, recvmessage.metadata, recvmessage.senderid)
            SEstatus = recvmessage.metadata[0]
            if ANALYSIS: numTotalMessages += recvmessage.metadata[2]
            for i,j in SEstatus.items():
                if j=="Branch":
                    mstAdjacencyMatrix[recvmessage.senderid][i] = 1
                    mstAdjacencyMatrix[i][recvmessage.senderid] = 1
            numStatusMessages+=1
        else:
            # if DEBUG: print("some other message")
            if DEBUG: print("some other message", recvmessage.typemessage, recvmessage.metadata, recvmessage.senderid)


    def formatNumber(num):
        if num % 1 == 0:
            return int(num)
        else:
            return num
    mstEdges = []
    for i in range(numNodes):
        for j in range(i+1,numNodes):
            if mstAdjacencyMatrix[i][j] == 1:
                mstEdges.append((i, j, formatNumber(adjacencyMatrix[i][j])))
    def sortfn(e):
        return e[2]
    mstEdges.sort(reverse=False,key = sortfn)
    for i in mstEdges:
        print(i)

    if ANALYSIS:
        # print("Number of messsages is ", numTotalMessages)
        # print(numTotalMessages)
        upperLimit = 2*numEdgesReal + math.ceil(5*numNodes*math.log2(numNodes))
        # print("upper limit is ", upperLimit)
        # print(upperLimit)
        print("n, edges, messages, upperlimit, nlogn")
        print(numNodes,str(","),numEdgesReal,str(","), numTotalMessages,str(","), upperLimit,str(","), int(numNodes*math.log2(numNodes)))
    if DEBUGOUTPUT:
        #kruskal
        from kruskal import Graph
        g = Graph(numNodes)
        for i in testEdges:
            g.addEdge(i[0],i[1],i[2])
        kruskalmst = g.KruskalMST()
        if DEBUG: print("kruskal answer is ", kruskalmst)
        kruskalMstAdjacencyMatrix = np.zeros((numNodes, numNodes))
        for i,j,k in kruskalmst:
            kruskalMstAdjacencyMatrix[i][j] = 1
            kruskalMstAdjacencyMatrix[j][i] = 1
        isVerified = True
        for i in range(numNodes):
            for j in range(numNodes):
                if(kruskalMstAdjacencyMatrix[i][j]!=mstAdjacencyMatrix[i][j]):
                    isVerified=False
                    break
            if(not isVerified):
                break
        print("GHS is ", isVerified)




