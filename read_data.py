# -*- coding: utf-8 -*-
"""
Created on Mon Aug  5 16:06:32 2024

@author: apeper
"""

#File to read data from csv files. 
#Note: data was originally created in a format that allows for multiple job modes.
#   All data we use only includes one mode. 
#   In the data file, all job data includes an extra mode index of 0.
#   Here we simplify the format of the data to not index by mode.

import csv
import sys


fileName = sys.argv[1]

# --------------------------------------------------------------------------------------
#Read in data from file
with open(fileName,"r") as f:
    reader = csv.reader(f)
        
    #General parameters
    keys = next(reader)
    values = [float(i) for i in next(reader)]
    params = dict(zip(keys,values))
    
    #Indexed by project
    next(reader) #Label row "Jobs per project"
    keys = [int(i) for i in next(reader)] 
    values = [int(i) for i in next(reader)]
    J = dict(zip(keys,values))
    
    next(reader) #Label row 'Complexity per project'
    keys = [int(i) for i in next(reader)]
    values = [float(i) for i in next(reader)]
    C = dict(zip(keys,values))
    
    
    #Indexed by Job
    next(reader) #Label row "Modes per job"
    keys = [int(i) for i in next(reader)]
    values = [int(i) for i in next(reader)]
    M = dict(zip(keys,values))
    
    #Indexed by Job and Mode
    next(reader) #Label row: "Job durations"
    keys = [int(i) for i in next(reader)]
    d = {}
    for i in keys:
        values_keys = [int(l) for l in next(reader)]
        values_values = [int(l) for l in next(reader)]
        sub_dict = dict(zip(values_keys,values_values))
        d[i] = sub_dict
        
    #Network stuff
    next(reader) #Label row: "Number of start jobs per project"
    keys = [int(i) for i in next(reader)]
    values = [int(i) for i in next(reader)]
    starts = dict(zip(keys,values))
    next(reader) #Label row: "Number of finish jobs per project"
    keys = [int(i) for i in next(reader)] 
    values = [int(i) for i in next(reader)]
    finishes = dict(zip(keys,values))
    next(reader) #Label row: "Edges: amount (total and per project) then pairs"
    e_tot = int(next(reader)[0]) #Just a single entry row, total amount of edges
    values = [int(i) for i in next(reader)] #amount of edges per project: Can divide list of edges using this if needed (uses prev keys)
    per_proj_amt_edges = dict(zip(keys,values))
    edges = []
    for i in range(e_tot):
        e = next(reader)
        edges.append((int(e[0]),int(e[1])))
    next(reader) #Label row: "Precedences for each job"
    keys = [int(i) for i in next(reader)]
    precs = {}
    for i in keys:
        precs[i] = [int(j) for j in next(reader)]
    
    #Resources
    next(reader) #Label row: 'len(job mode resource) and does this job mode use this resource'
    keyLen = int(next(reader)[0])
    keys = []
    for i in range(keyLen): #Create keys of dictionary (they are tuples so gotta be more difficult)
        key = next(reader)
        keys.append((int(key[0]),int(key[1]),int(key[2])))
    values = [int(i) for i in next(reader)]
    dem = dict(zip(keys,values))
    next(reader) #Label row: 'len(time resource) and amount avail per time period per resource'
    keyLen = int(next(reader)[0])
    keys = []
    for i in range(keyLen): #Create keys of dictionary (they are tuples so gotta be more difficult)
        key = next(reader)
        keys.append((int(key[0]),int(key[1])))
    values = [int(i) for i in next(reader)]
    avail = dict(zip(keys,values))
    
        
    #Vulnerabilities
    next(reader) #Label row: 'len(job node) and how much does this job cover this node'
    keyLen = int(next(reader)[0])
    mitigations = [] #Also want to keep track of which of these jobs are mitigations (for usefulness later)
    keys = []
    for i in range(keyLen): #Create keys of dictionary (they are tuples so gotta be more difficult)
        key = next(reader)
        keys.append((int(key[0]),int(key[1])))
        if int(key[0]) not in mitigations:
            mitigations.append(int(key[0]))
    values = [float(i) for i in next(reader)]
    pre_w = dict(zip(keys,values))
    
    next(reader) #Label row: 'len(nodes) x,y for each node'
    keys = [int(i) for i in next(reader)]
    fcoords = {}
    for n in keys:
        fcoords[n] = {}
        fcoords[n]['x'] = [float(i) for i in next(reader)]
        fcoords[n]['y'] = [float(i) for i in next(reader)]

    
    f.close()
    
# -----------------------------------------------------------------------------------------
#Simplify data format
jobs = range(2,int(params['num_jobs'])) #Jobs 0 and 1 are the global start and finish jobs. Not real jobs.
modes = dict(zip(jobs,[range(M[j]) for j in jobs] )) 
resources = range(int(params['num_resources']))
nodes = range(int(params['num_nodes']))

T = int(params['time_horizon'])
budget = avail[0,params['num_resources']] #Final resource is the non-renewable resource

#Precedences
P = []
for (i,j) in edges:
    if i != 0 and j != 1: #Don't worry about ones that start/finish with the source/sink
        P.append((i,j))
        
# ----------------------------------------------------------------------------------------

#Add in the 0 weights for non-mitigating jobs
w={}
for n in nodes:
    for j in jobs:
        if j not in mitigations:
            w[j,n] = 0
        else:
            w[j,n] = pre_w[j,n]
    
# -----------------------------------------------------------------------------------------

#We only use one mode per job, make notation match that:
job_modes = [(j,0) for j in jobs]
#duration of each job
p = dict(zip(jobs,[d[j][m] for (j,m) in job_modes])) 
#resources consumed by each job
c = dict(zip([(j,r) for j in jobs for r in resources],[dem[j,m,r] for (j,m) in job_modes for r in resources]))
#nonrenewable budget resource:
for (j,m) in job_modes:
    c[j,int(params['num_resources'])] = dem[j,m,int(params['num_resources'])]
    
# ------------------------------------------------------------------------------------------

a = {} #Time weights

#Using an exponential function to determine time weighting

exp_base = params['exp_base']
for t in range(T):
    a[t] = exp_base**t
a[T] = 0 #For use in the objective function, we get no reward for jobs completed after the time horizon
