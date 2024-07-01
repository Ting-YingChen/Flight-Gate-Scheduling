import pandas as pd

# Configurations for data import
LOCAL_PATH = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'

# Data Import Functions
def import_data(local_path):
    """ Imports various data sheets from an Excel file. """
    # Flights
    flights = pd.read_excel(local_path, sheet_name='EBBR - Flights', usecols='A:Z', header=1, index_col=0)
    num_flights = len(flights)

    # Gates
    gates = pd.read_excel(local_path, sheet_name='EBBR - Gates (length)', usecols='A:G', header=0, index_col=0)
    num_gates = len(gates)

    # T Matrix (Time Differences)
    T_timeDiff = pd.read_excel(local_path, sheet_name='EBBR - Flights (T matrix)', usecols='A:FP', header=0, index_col=0, nrows=num_flights)

    # Gates Neighbours and Distances
    Gates_N = pd.read_excel(local_path, sheet_name='EBBR - Gates (next)', usecols='A:DA', header=0, index_col=0, nrows=num_gates)
    Gates_D = pd.read_excel(local_path, sheet_name='EBBR - Gates (dist)', usecols='A:CA', header=0, index_col=0, nrows=num_gates)

    return flights, gates, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates

# Import data
flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates = import_data(LOCAL_PATH)

# Processing functions for flight and gate data
def process_data(flights, gates):
    """ Processes flight and gate data to extract relevant operational matrices and mappings. """
    # Flight and gate details
    Flight_No = flights.index.tolist()
    Gate_No = [str(x) for x in gates.index]

    # Additional flight data
    ETA = flights['ETA']
    ETD = flights['ETD']

    return Flight_No, Gate_No, ETA, ETD

# Process data
Flight_No, Gate_No, ETA, ETD = process_data(flightsBrussels, gatesBrussels)

# Preferences setup
def build_preferences_dict(flights):
    """ Builds a dictionary of flight preferences. """
    return {idx: row[['Pref. Int', 'Pref. EU (normal)', 'Pref. EU\n(low cost)', 'Pref. Close']].tolist() for idx, row in flights.iterrows()}

# Build preferences
P_preferences = build_preferences_dict(flightsBrussels)

# Successor function and gate assignments
def build_Udict(Flight_No):
    """ Builds a successor function dictionary. """
    return {flight: [3 * flight -2, 3 * flight, 0] for flight in Flight_No}

def build_Mdict(AC_size, Max_Wingspan, P_preferences, Is_Int):
    """ Builds valid gate assignments for each flight. """
    Mdict = {}
    for flight in Flight_No:
        valid_gates = [gate for gate in Gate_No if AC_size.loc[flight] <= Max_Wingspan.loc[gate] and (P_preferences[flight][0] / 10 == Is_Int.loc[gate] or Is_Int.loc[gate] == 2)]
        Mdict[flight] = valid_gates + ['Dum']  # Include dummy gate
    return Mdict

# Setup U and M dictionaries
U_successor = build_Udict(Flight_No)
M_validGate = build_Mdict(flightsBrussels['AC size (m)'], gatesBrussels['Max length (m)'], P_preferences, gatesBrussels['International'])

# Shadow constraints based on operational needs
def build_ShadowConstraints(Flight_No, ETA, ETD, M_validGate, Gates_N):
    """ Constructs shadow constraints based on flight scheduling logic. """
    shadow_constraints = []
    for flight1 in Flight_No:
        for flight2 in Flight_No:
            if ETA.loc[flight2] < ETD.loc[flight1] and flight2 > flight1:  # Check if flight2 lands before flight1 departs
                for gate1 in M_validGate[flight1]:
                    for gate2 in M_validGate[flight2]:
                        if Gates_N.loc[gate1, gate2] in {1, -1} and gate1 != 'Dum' and gate2 != 'Dum':
                            shadow_constraints.append((flight1, gate1, flight2, gate2))
    return shadow_constraints

# Build shadow constraints
shadow_constraints = build_ShadowConstraints(Flight_No, ETA, ETD, M_validGate, Gates_N)

# Parameters based on experiences
alpha1 = 1  # Preference scaling factor
alpha2 = 20  # Reward for avoiding tows
alpha3 = 100  # Penalty scaling factor for buffer time deficits
t_max = 30

#'''
######################################### print something to check #####################################################

# Print the first few rows of the flights data to confirm correct loading and indexing
print("First few flights data:")
print(flightsBrussels.head())

# Print the first few rows of the gates data to verify correct loading
print("\nFirst few gates data (num_gates):")
print(gatesBrussels.head())

print("\nFlight_No:", Flight_No)
print("Gate_No:", Gate_No)

print("\nnum_flights:", num_flights)
print("num_gates:", num_gates)

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


