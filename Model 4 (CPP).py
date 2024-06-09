### Model 4 (CPP) ###

import pandas as pd
from gurobipy import Model, GRB, quicksum

# Inputs
''' For now: change path of file here under'''
''' Later: put excels in same directory!!! '''
flightCount = len(pd.read_excel('/Users/chentingying/Documents/tum/Ad_Se_Operation_Management/Airports_data/Brussels_Clean.xlsm', sheet_name='EBBR - Flights', usecols='A:T', skiprows=2))
flightsBrussels = pd.read_excel('/Users/chentingying/Documents/tum/Ad_Se_Operation_Management/Airports_data/Brussels_Clean.xlsm', usecols='A:T', skiprows=1, nrows=flightCount)
n = flightCount # Number of flights

gateCount = len(pd.read_excel('/Users/chentingying/Documents/tum/Ad_Se_Operation_Management/Airports_data/Brussels_Clean.xlsm', sheet_name='EBBR - Gates', usecols='A:D', skiprows=1))
gatesBrussels = pd.read_excel('/Users/chentingying/Documents/tum/Ad_Se_Operation_Management/Airports_data/Brussels_Clean.xlsm', sheet_name='EBBR - Gates', usecols='A:D', skiprows=0, nrows=gateCount)
m = gateCount # Number of gates

# Flight columns
Flight_No = flightsBrussels['Flight']   # Aircrafts' flight number @ arrival
ETA = flightsBrussels['ETA']
ETD = flightsBrussels['ETD']
E_Parking = flightsBrussels['Planned Duration']
RTA = flightsBrussels['RTA']
RTD = flightsBrussels['RTD']
R_Parking = flightsBrussels['Real Duration']
Tot_Delay = flightsBrussels['Total Delay']
AC_size = flightsBrussels['AC size (m)']

# Tests
FN2 = Flight_No.tolist()

# Gates columns
Gate_Name = gatesBrussels['Name']
Max_Wingspan = gatesBrussels['Max length (m)']   # Max wingspan allowed on that gate

'''No idea what this is'''
# T = [
#     [0, 10, 15, 20],  # Flight 1 can sequentially follow Flights 2, 3, 4
#     [10, 0, 15, 25],  # Flight 2 can sequentially follow Flights 1, 3, 4
#     [15, 15, 0, 30],  # Flight 3 can sequentially follow Flights 1, 2, 4
#     [20, 25, 30, 0]   # Flight 4 can sequentially follow Flights 1, 2, 3
# ]

# Building U -> U[i] = successor of i (=0 if no successor)
U = []
for i in range(n):
    U.extend([3*i+1, 3*i+2, 0])     # U = [1,2,0, 4,5,0, ...]
# print(f"U = {U}")

'''
i = 0,1,2 = "Landing", "Parking" and "Departure" index for the 1st flight of the day; i = 3,4,5 = ...
U[1] = 2    -> Parking of 1st flight has Departure of 1st flight as successor
U[5] = 0    -> Departure of 2nd flight has no successor
i%3 = 0     -> landing of a flight x,     with x = (i-i%3)/3 
i%3 = 1     -> parking of a flight x,     with x = (i-i%3)/3 
i%3 = 2     -> departure of a flight x,   with x = (i-i%3)/3 
'''

# Building M
M = Gate_Name.tolist()
'''
For now: M = [0,1,2,...] = allowed gates for ALL flights
Later: make it [[0, 3, 50, ...], ...] when we have preferences for each flights individually
'''

alpha1 = 1   # Preference scaling factor
alpha2 = 50  # Reward for avoiding tows
alpha3 = 5   # Penalty scaling factor for buffer time deficits

t_max = 30

# Shadow Restrictions
shadow_restrictions = [
    (0, 0, 1, 1), # Activity 1 at Gate 0 and Activity 2 at Gate 1 cannot happen
    (2, 2, 3, 1)  # Activity 3 at Gate 2 and Activity 4 at Gate 1 cannot happen
]




















