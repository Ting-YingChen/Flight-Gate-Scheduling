import pandas as pd

'''
Importing the following data from the instance:
 - Flights
 - Gates
 - T matrix
 - Gates and neighbours matrix (1 if gate i and j are neighbours, 0 if not, -1 if i = j)
 - Gates distances matrix (distances between all gates)
'''

# Use latest excel (for now, change "local_path" to represent actual directory)
local_path = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'

# Importing flights
flightCount = len(pd.read_excel(local_path, sheet_name='EBBR - Flights', header=1, usecols='A:A'))   # "header" = labels of columns (0 = 1st row)
flightsBrussels = pd.read_excel(local_path, usecols='A:Z', header=1, index_col=0, skiprows=0, nrows=flightCount)   # index_col = labels of rows

# print(flightsBrussels)

# Importing gates
gateCount = len(pd.read_excel(local_path, sheet_name='EBBR - Gates (length)', header=0, usecols='A:A'))
gatesBrussels = pd.read_excel(local_path, sheet_name='EBBR - Gates (length)', header=0, index_col=0, usecols='A:G', nrows=gateCount)
'''last row = dummy gate'''

# print(gatesBrussels)

# Importing "T" matrix
T_matrix = pd.read_excel(local_path, sheet_name='EBBR - Flights (T matrix)', header=0, index_col=0, usecols='A:FP', nrows=flightCount)

# print(T_matrix)

# Importing "gates and neighbours" and "gates distances) matrix
Gates_N = pd.read_excel(local_path, sheet_name='EBBR - Gates (next)', header=0, index_col=0, usecols='A:CA', nrows=gateCount)
Gates_D = pd.read_excel(local_path, sheet_name='EBBR - Gates (dist)', header=0, index_col=0, usecols='A:CA', nrows=gateCount)

# print(Gates_N)
# print("------------")
# print(Gates_D)

'''
T = matrix of time differences
P = preferences matrix
alpha1, alpha2, alpha3 = weight factors
t_max = maximum buffer time
U = successor function
M = valid gate assignments for each flight
'''

# Sets
num_flights = flightCount  # Number of flights
num_gates = gateCount  # Number of real gates + dummy gate

# Flight columns                                (X.iloc[0] to access first row of variable X)
Flight_No = flightsBrussels.index.tolist()  # List of integers
ETA = flightsBrussels['ETA']
ETD = flightsBrussels['ETD']
E_Parking = flightsBrussels['Planned Duration']
RTA = flightsBrussels['RTA']
RTD = flightsBrussels['RTD']
R_Parking = flightsBrussels['Real Duration']
Tot_Delay = flightsBrussels['Total Delay']
AC_size = flightsBrussels['AC size (m)']
Pref = flightsBrussels[['Pref. Int', 'Pref. EU (normal)', 'Pref. EU\n(low cost)', 'Pref. Close']]
# Preferences for International gate
# EU gate (not low-cost)
# EU gate (low-cost)
# Gate close to (passenger) exit
preferences = Pref.values.tolist()
# preferences[2] = [a,b,c,d] = all 4 levels of preferences (0 to 10) for flight 3


# Gates columns
Gate_No = [str(x) for x in gatesBrussels.index]  # List of STRINGS (Gate "140L" cannot be converted to int)
Max_Wingspan = gatesBrussels['Max length (m)']  # Max wingspan allowed on that gate
Is_Int = gatesBrussels['International']  # 1 if international,   0 if not, 2 if dummy gate
Is_LowCost = gatesBrussels['Low cost']  # 1 if low cost,        0 if not, 2 if dummy gate
Is_Close = gatesBrussels['Close']  # 1 if close,           0 if not, 2 if dummy gate

# T matrix
T = T_matrix.values.tolist()

# Preferences matrix
P = []

# U list of successors (U[i] = successor of i, 0 if no successor)
U = []
for i in range(num_flights):
    # U.append([3*i+1, 3*i+2, 0])   # U = [[1,2,0], [4,5,0],  ...]
    U.extend([3 * i + 1, 3 * i + 2, 0])  # U = [1,2,0,    4,5,0,   ...]
# print(f"U = {U}")

'''
i = 0,1,2 = "Landing", "Parking" and "Departure" index for the FIRST flight of the day; i = 3,4,5 = ...
U[1] = 2    -> Parking of 1st flight has Departure of 1st flight as successor
U[5] = 0    -> Departure of 2nd flight has no successor
U[i] with
i%3 = 0     -> landing of a flight x,     with x = (i-i%3)/3 
i%3 = 1     -> parking of a flight x,     with x = (i-i%3)/3 
i%3 = 2     -> departure of a flight x,   with x = (i-i%3)/3 
'''

# Building M

# For now: M = [0,1,2,...] = allowed gates for ALL flights
# Later: make it [[0, 3, 50, ...], ...] when we have preferences for each flight individually
''' -> Done'''

Mlist = []  # Set of all gates M(i) allowed for the flight i, this for all flights
for flight in Flight_No:
    Msub = []
    for gate in Gate_No:
        PlaneFits = AC_size.loc[flight] <= Max_Wingspan.loc[gate]  # Is the gate wide enough for the plane
        GoodGate = preferences[flight - 1][0] / 10 == Is_Int.loc[
            gate]  # Is the gate Int if flight is Int, or ... EU if ... EU
        if PlaneFits and GoodGate:
            Msub.append(gate)

    Msub.append('Dum')  # Add dummy gate to M(i) for all i
    Mlist.append(Msub)  # Add M(i) to a list of all M(i)s


def TestAndCheck_M(flight: int):
    f = flight
    intern = ''
    if preferences[flight - 1][0] == 10:
        intern = 'international'
    else:
        intern = 'european'
    print(f"Flight of index {f} is an {intern} flight, with a wingspan of {AC_size.loc[f + 1]}m.")
    print("The allowed gates for it are:")
    for i in range(len(Mlist[f])):
        print(f"- gate {Mlist[f][i]} with a width of {Max_Wingspan.loc[Mlist[f][i]]}m")

    return


# TestAndCheck_M(4)

alpha1 = 1  # Preference scaling factor
alpha2 = 20  # Reward for avoiding tows
alpha3 = 100  # Penalty scaling factor for buffer time deficits

t_max = 30

'''
shadow_constraints should be a list of 4-tuples (i, k, j, l) 
indicating that activity i can’t occur at gate k while activity j occurs at gate l.
'''
shadow_constraints = [
    # Constraint to avoid timing overlaps
    (0, 0, 1, 0),  # If Flight 1 is at Gate 1, Flight 2 should not be at Gate 1 due to overlap
    (1, 1, 2, 1),  # If Flight 2 is at Gate 2, Flight 3 should not be at Gate 2
    (3, 0, 4, 0),  # If Flight 4 is at Gate 1, Flight 5 should not be at Gate 1
    (5, 2, 0, 2),  # If Flight 6 is at Gate 3, Flight 1 should not be at Gate 3

    # Constraints to restrict the usage of Dummy Gate (assuming index 2 as Dummy Gate)
    (0, 2, 1, 2),  # If Flight 1 uses Dummy Gate, no other flights should use it
    (1, 2, 2, 2),  # If Flight 2 uses Dummy Gate, no other flights should use it
    (3, 2, 4, 2),  # If Flight 4 uses Dummy Gate, no other flights should use it

    # Specific restrictions for other logistical reasons
    (2, 1, 3, 1),  # If Flight 3 is at Gate 2, Flight 4 should not be at Gate 2
    (4, 0, 5, 0),  # If Flight 5 is at Gate 1, Flight 6 should not be at Gate 1
]


