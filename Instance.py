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
local_path = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'

# Importing flights
flightCount = len(pd.read_excel(local_path, sheet_name='EBBR - Flights', header=1, usecols='A:A'))   # "header" = labels of columns (0 = 1st row)
flightsBrussels = pd.read_excel(local_path, usecols='A:Z', header=1, index_col=0, skiprows=0, nrows=flightCount)   # index_col = labels of rows
#print(flightsBrussels)

# Importing gates
gateCount = len(pd.read_excel(local_path, sheet_name='EBBR - Gates (length)', header=0, usecols='A:A'))
gatesBrussels = pd.read_excel(local_path, sheet_name='EBBR - Gates (length)', header=0, index_col=0, usecols='A:G', nrows=gateCount)
'''last row = dummy gate'''
# print(f'gateCount = {gateCount}')
#print(gatesBrussels)

# Importing "T" matrix
T_matrix = pd.read_excel(local_path, sheet_name='EBBR - Flights (T matrix)', header=0, index_col=0, usecols='A:FP', nrows=flightCount)
#print(T_matrix)

# Importing "Gates Neighbours" and "Gates Distances" matrix
Gates_N = pd.read_excel(local_path, sheet_name='EBBR - Gates (next)', header=0, index_col=0, usecols='A:DA', nrows=gateCount)
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
num_flights = flightCount   # Number of flights
num_gates = gateCount       # Number of real gates + dummy gate

# Flight columns                                (X.iloc[0] to access first row of variable X)
Flight_No = flightsBrussels.index.tolist()      # List of integers
ETA = flightsBrussels['ETA']
ETD = flightsBrussels['ETD']
E_Parking = flightsBrussels['Planned Duration']
RTA = flightsBrussels['RTA']
RTD = flightsBrussels['RTD']
R_Parking = flightsBrussels['Real Duration']
Tot_Delay = flightsBrussels['Total Delay']
AC_size = flightsBrussels['AC size (m)']
pref = flightsBrussels[['Pref. Int', 'Pref. EU (normal)', 'Pref. EU\n(low cost)', 'Pref. Close']].values.tolist()
    # Preferences for International gate
    # EU gate (not low-cost)
    # EU gate (low-cost)
    # Gate close to (passenger) exit
# pref = Pref.values.tolist()      # preferences[2] = [a,b,c,d] = all 4 levels of preferences (0 to 10) for flight 3

def pref_to_dict(Flight_No, pref):
    preferences = {}
    for flight in Flight_No:
        preferences[flight] = pref[flight - 1]
    return preferences

P_preferences = {}
for flight in Flight_No:
    P_preferences[flight] = pref[flight - 1]

def real_Pref(AC_size, Max_Wingspan, preferences, Is_Int, Is_Close):
    realPref = {}
    for flight in Flight_No:
        prefSub = {}
        for gate in Gate_No:
            score = 0   # Score of preferences (higher = more preferred)
            PlaneFits = AC_size.loc[flight] <= Max_Wingspan.loc[gate]   # Is the gate wide enough for the plane
            GoodGate = (preferences[flight][0] / 10 == Is_Int.loc[gate]) or Is_Int.loc[gate] == 2
                # Flight and gate are both International/EU, or the gate is remote (remote = open for all)
            IsDummyGate = Is_Int.loc[gate] == -1
            if PlaneFits and GoodGate and not IsDummyGate:
                # Adapt score as wished
                score += 100        # +100pts for gates big enough and international / EU
                if preferences[flight][1] == 10 and Is_LowCost == 0:    # if flight prefers normal EU and gate is normal EU
                    score += 20
                elif preferences[flight][2] == 10 and Is_LowCost == 1:  # if flight prefers low-cost EU and gate is low-cost EU
                    score += 20
                elif Is_Close == 1:                                     # if gate is close (preferences[][] = -10, 0 or +10)
                    score += preferences[flight][3]*3
                elif Is_Close == -1:                                    # if gate is remote
                    score -= 50
                prefSub[gate] = score   # Add score (value) of current gate (key) to a sub-dictionary

            elif IsDummyGate:
                score = 50             # Choose what level of preferences is wanted to assign to the dummy gate
                prefSub[gate] = score   # Add score (value) of current gate (key) to a sub-dictionary

        realPref[flight] = prefSub      # Add sub-dictionnary (value) of current flight (key) to a main-dictionary

    return realPref


# Gates columns
Gate_No = [str(x) for x in gatesBrussels.index]     # List of STRINGS (Gate "140L" cannot be converted to int)
Max_Wingspan = gatesBrussels['Max length (m)']      # Max wingspan allowed on that gate
Is_Int = gatesBrussels['International']             # 1 if international,   0 if not, 2 if dummy gate
Is_LowCost = gatesBrussels['Low cost']              # 1 if low cost,        0 if not, 2 if dummy gate
Is_Close = gatesBrussels['Close']                   # 1 if close,           0 if not, 2 if dummy gate

# U list of successors (U[i] = successor of i, 0 if no successor)
def build_Udict(Flight_No):
    Udict = {}
    for flight in range(len(Flight_No)):
        Udict[flight] = [3 * flight - 1, 3 * flight + 2, 0]
    return Udict

# Building M
def build_Mdict(AC_size, Max_Wingspan, preferences, Is_Int):
    Mdict = {}  # Dictionary to store the gates allowed for each flight
    for flight in Flight_No:
        Msub = []   # Gates allowed for the flight 'flight'
        for gate in Gate_No:
            PlaneFits = AC_size.loc[flight] <= Max_Wingspan.loc[gate]
            GoodGate = preferences[flight][0] / 10 == Is_Int.loc[gate] or Is_Int.loc[gate] == 2
            if PlaneFits and GoodGate:
                Msub.append(gate)

        Msub.append('Dum')  # Add dummy gate to M(i) for all i
        Mdict[flight] = Msub  # Add M(i) to the dictionary with the flight as key

    return Mdict
# print(f"The result is: {build_Mdict(AC_size, Max_Wingspan, preferences, Is_Int)}")

'''
def TestAndCheck_M(flight: int, Mlist):
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
'''

alpha1 = 1  # Preference scaling factor
alpha2 = 20  # Reward for avoiding tows
alpha3 = 100  # Penalty scaling factor for buffer time deficits
t_max = 30

'''
shadow_constraints should be a list of 4-tuples (i, k, j, l) 
indicating that activity i can’t occur at gate k while activity j occurs at gate l.
'''
def build_ShadowConstraints(FLight_No, ETAorRTA, ETDorRTD, Mdict, Gates_N):
    all_SC = []
    for flight1 in Flight_No:
        for flight2 in Flight_No: # flight2 > flight1:
            # SC1, SC2 = ()
            LandsBefore = ETAorRTA.loc[flight2] < ETDorRTD.loc[flight1]     # Check if they are simultaneously at the airport
            if LandsBefore and flight2 > flight1:
                '''
                Correct assumption to only check for next flights?
                If we check for before, we would have duplicates of shadow constraints no?
                '''
                for gate_f1 in Mdict[flight1]:
                    for gate_f2 in Mdict[flight2]:
                        GatesAreNext = Gates_N.loc[gate_f1, gate_f2] == 1       # Check if gates are next to each other
                        GatesAreSame = Gates_N.loc[gate_f1, gate_f2] == -1      # Check if they are the same gates
                        '''GatesAreSame necessary? Or also checked elsewhere that two flights cannot be on the same gate'''
                        if (GatesAreNext or GatesAreSame) and (gate_f1 != 'Dum' and gate_f1 != 'Dum'):
                            SC1 = (flight1, gate_f1, flight2, gate_f2)
                            # SC2 = (flight2, gate_f2, flight1, gate_f1)
                            '''Necessary to have the symmetric no?'''
                            all_SC.append(SC1)
                            # all_SC.append(SC2)
    return all_SC


# T, P, U, M, shadow_constraints

T_timeDiff = T_matrix.values.tolist()
P_preferences = pref_to_dict(Flight_No=Flight_No, pref=pref)
U_successor = build_Udict(Flight_No)
M_validGate = build_Mdict(AC_size=AC_size, Max_Wingspan=Max_Wingspan, preferences=P_preferences, Is_Int=Is_Int)
shadow_constraints = build_ShadowConstraints(Flight_No, ETAorRTA=ETA, ETDorRTD=ETD, Mdict=M_validGate, Gates_N = Gates_N)
#print(f'There are {len(shadow_constraints)} shadow constraints.')

#'''
######################################### print something to check #####################################################

# Print the first few rows of the flights data to confirm correct loading and indexing
print("First few flights data:")
print(flightsBrussels.head())

# Print the first few rows of the gates data to verify correct loading
print("\nFirst few gates data (num_gates):")
print(gatesBrussels.head())

# Check a slice of the T matrix to ensure it's properly loaded
print("\nSample of T matrix (T_timeDiff):")
print(T_timeDiff.iloc[:5, :5])

# Print details of the Gates Neighbours and Gates Distances matrices
print("\nGates Neighbours Matrix Sample:")
print(Gates_N.iloc[:5, :5])
print("\nGates Distances Matrix Sample:")
print(Gates_D.iloc[:5, :5])

# Print the total number of flights and gates to validate counts
print("\nTotal number of flights:", num_flights)
print("Total number of gates:", num_gates)

# Print the first few entries of flight preferences to check if they are captured correctly
print("\nFlight Preferences Sample (P_preferences):")
for key, value in list(P_preferences.items())[:5]:
    print(f"Flight {key}: {value}")

# Print a few entries from the U successor function dictionary
print("\nSuccessor function sample (U_successor):")
for key, value in list(U_successor.items())[:5]:
    print(f"Flight {key}: Successors {value}")

# Print a few entries from the M gate assignments dictionary
print("\nValid gate assignments sample (M_validGate):")
for key, value in list(M_validGate.items())[:5]:
    print(f"Flight {key}: Valid gates {value}")

# Print the first few shadow constraints to ensure they're being constructed correctly
print("\nShadow Constraints Sample:")
print(shadow_constraints[:5])
# '''













