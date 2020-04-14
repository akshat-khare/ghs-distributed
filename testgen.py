import sys
import random 
nodes = int(sys.argv[1])
edges = int(sys.argv[2])
outf = open(sys.argv[3], 'w')
outf.write(str(nodes))
outf.write('\n')
edgeSet = set()
weightSet = set()

for i in range(nodes-1):
    n = random.randint(i+1, nodes-1)
    edgeSet.add((i,n))

while len(edgeSet) != edges:
    n1 = random.randint(0,nodes-1)
    n2 = random.randint(0,nodes-1)
    if n1!=n2:
        edgeSet.add((min(n1,n2), max(n1,n2)))

while len(weightSet) != edges:
    ew = random.randint(1,edges)
    weightSet.add(ew)

edgeSet = list(edgeSet)
weightSet = list(weightSet)
for i in range(edges):
    outf.write(str((edgeSet[i][0], edgeSet[i][1], weightSet[i])))
    outf.write('\n')