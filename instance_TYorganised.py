import pandas as pd
import datetime

# Configurations for data import
# LOCAL_PATH = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels copy.xlsm'

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

# # Import data
# flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates = import_data(LOCAL_PATH)

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

# # Process data
# Flight_No, Gate_No, ETA, ETD = process_data(flightsBrussels, gatesBrussels)

# Preferences setup
def build_preferences_dict(flightsBrussels, Is_Int, Is_LowCost, Is_Close, Flight_No, M_validGate):
    """ Builds a dictionary of flight preferences. """
    P_preferences = {}  # keys: flights, values: dictionary with keys = gate IDs, values = assigned preference
    for flight in Flight_No:
        P_preferences[flight] = {}
        for gate in M_validGate[flight]:
            # for dummy gate: set preference to some large negative value
            if gate == "Dum":
                P_preferences[flight][gate] = -1000
            else:
                # international flights need to be treated different from EU ones
                flight_is_international = flightsBrussels.loc[flight, "Pref. Int"] != 0
                if flight_is_international:
                    # if flight seems to be international but valid gate is EU: raise an error
                    if Is_Int[gate] == 0:
                        raise Exception("Flight seems to be international, but can be assigned to a EU gate!")
                    # else: assign corresponding preference
                    else:
                        P_preferences[flight][gate] = flightsBrussels.loc[flight, "Pref. Int"]

                # for EU flights: get info on gate type (international, low cost) and assign respective preference
                else:
                    if Is_Int[gate] == 2:
                        P_preferences[flight][gate] = flightsBrussels.loc[flight, "Pref. Int"]
                    if Is_LowCost[gate]:
                        P_preferences[flight][gate] = flightsBrussels.loc[flight, "Pref. EU (low cost)"]
                    elif Is_Close[gate]:
                        P_preferences[flight][gate] = flightsBrussels.loc[flight, "Pref. Close"]
                    # if gate is neither international nor low cost: must be normal EU gate
                    else:
                        P_preferences[flight][gate] = flightsBrussels.loc[flight, "Pref. EU (normal)"]

    return P_preferences
# Build preferences
# P_preferences = build_preferences_dict(flightsBrussels)


def createActivitiesFromFlights(Flight_No, flightsBrussels):
    '''map flights to activities (arrivals, departures, parking [if possible]).
    also creates a successor dictionary udict.
    '''
    flights_to_activities = {} # keys: flight no., values: list of all activities associated with respective flight
    activities_to_flights = {} # inverse dictionary of flights_to_activities
    Udict = {}
    no_towable_flights = 0  # counts the number of flights that can theoretically be towed

    for flight in Flight_No:
        arrival = flightsBrussels.loc[flight, "RTA"]
        departure = flightsBrussels.loc[flight, "RTD"]
        is_turnaround = None
        # todo: add some condition on whether or not flight can be towed during layover
        # example: layover > 60 minutes => flight can be towed
        dep_datetime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), departure)
        arr_datetime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), arrival)
        layover_seconds = dep_datetime - arr_datetime
        is_towable = layover_seconds > datetime.timedelta(seconds=3600)
        # map flights to activities
        flights_to_activities[flight] = [f"arrival_{flight}", f"departure_{flight}"]
        Udict[f"departure_{flight}"] = 0    # departures activity has no successor
        if is_towable:
            no_towable_flights += 1
            flights_to_activities[flight].append(f"parking_{flight}")
            Udict[f"arrival_{flight}"] = f"parking_{flight}"
            Udict[f"parking_{flight}"] = f"departure_{flight}"
        else:
            Udict[f"arrival_{flight}"] = f"departure_{flight}"


        # also map activities to flights
        activities_to_flights[f"arrival_{flight}"] = flight
        activities_to_flights[f"departure_{flight}"] = flight
        if is_towable:
            activities_to_flights[f"parking_{flight}"] = flight

    # Calculate the total number of activities
    num_activities = sum(len(acts) for acts in flights_to_activities.values())

    return flights_to_activities, activities_to_flights, num_activities, Udict, no_towable_flights

# flights_to_activities, activities_to_flights, U_successor = createActivitiesFromFlights(Flight_No, flightsBrussels)


# Successor function and gate assignments
# def build_Udict(Flight_No):
#     """ Builds a successor function dictionary. """
#     return {flight: [3 * flight -2, 3 * flight, 0] for flight in Flight_No}

def build_Mdict(AC_size, Pref_Int, Max_Wingspan, Is_Int, Flight_No, Gate_No):
    """ Builds valid gate assignments for each flight. """
    Mdict = {}
    for flight in Flight_No:
        valid_gates = [gate for gate in Gate_No if AC_size.loc[flight] <= Max_Wingspan.loc[gate] and (Pref_Int[flight] / 10 == Is_Int.loc[gate] or Is_Int.loc[gate] == 2)]
        # valid_gates = [gate for gate in Gate_No if AC_size.loc[flight] <= Max_Wingspan.loc[gate] and (P_preferences[flight][0] / 10 == Is_Int.loc[gate] or Is_Int.loc[gate] == 2)]
        Mdict[flight] = valid_gates + ['Dum']  # Include dummy gate
    return Mdict

# # Setup M dictionary
# # U_successor = build_Udict(Flight_No)
# M_validGate = build_Mdict(flightsBrussels['AC size (m)'], gatesBrussels['Max length (m)'], P_preferences, gatesBrussels['International'])

# Shadow constraints based on operational needs
def build_ShadowConstraints(Flight_No, ETA, ETD, M_validGate, Gates_N):
    """ Constructs shadow constraints based on flight scheduling logic. """
    # preprocessing: store information on neighbouring or identical gates. Reduces runtime by >90%
    GatesAreNext = {}
    GatesAreSame = {}
    for gate_f1 in Gates_N.index:
        for gate_f2 in Gates_N.columns:
            GatesAreNext[(gate_f1, gate_f2)] = Gates_N.loc[gate_f1, gate_f2] == 1
            GatesAreSame[(gate_f1, gate_f2)] = Gates_N.loc[gate_f1, gate_f2] == -1  # Check if they are the same gates


    shadow_constraints = []
    for flight1 in Flight_No:
        for flight2 in Flight_No:
            if ETA.loc[flight2] < ETD.loc[flight1] and flight2 > flight1:  # Check if flight2 lands before flight1 departs
                for gate1 in M_validGate[flight1]:
                    for gate2 in M_validGate[flight2]:
                        if (GatesAreNext[(gate1, gate2)] or GatesAreSame[(gate1, gate2)]) and gate1 != 'Dum' and gate2 != 'Dum':
                            shadow_constraints.append((flight1, gate1, flight2, gate2))
    return shadow_constraints

def mapGatesToIndices(Gates_N):
    '''Assign a unique index, starting from 1, to each gate. Used to create the weight matrix for the CPP.
    '''
    gates_to_indices = {}   # keys: gate names, values: index corresponding to gate
    indices_to_gates = {}   # inverse of gates_to_indices

    it = 1
    for gate in Gates_N.index:
        if gate != "Dum":   # skip dummy gate, because it will not be part of the CPP MIP model
            gates_to_indices[gate] = it
            indices_to_gates[it] = gate
            it += 1

    return gates_to_indices, indices_to_gates

# Function that reads input data and generates all relevant data structures
def createInputData(local_path, check_output):
    '''Create all needed data structured required as input for the MIP or the heuristic.
    '''
    flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates = import_data(local_path)
    # Process data
    Flight_No, Gate_No, ETA, ETD = process_data(flightsBrussels, gatesBrussels)
    # Create activities and generate successor function
    flights_to_activities, activities_to_flights, num_activities, U_successor, no_towable_flights = createActivitiesFromFlights(Flight_No, flightsBrussels)
    # Create feasible gate dictionary M
    M_validGate = build_Mdict(flightsBrussels['AC size (m)'], flightsBrussels["Pref. Int"], gatesBrussels['Max length (m)'],
                              gatesBrussels['International'], Flight_No, Gate_No)
    # Build preferences
    P_preferences = build_preferences_dict(flightsBrussels, gatesBrussels['International'], gatesBrussels['Low cost'],
                                           gatesBrussels["Close"], Flight_No, M_validGate)
    # Build shadow constraints
    shadow_constraints = build_ShadowConstraints(Flight_No, ETA, ETD, M_validGate, Gates_N)

    # map gate IDs to indices
    gates_to_indices, indices_to_gates = mapGatesToIndices(Gates_N)

    # if desired: print some sample data from the results
    if check_output:
        # Print the first few rows of the flights data to confirm correct loading and indexing
        print("First few flights data:")
        print(flightsBrussels.head())

        # Print the first few rows of the gates data to verify correct loading
        print("\nFirst few gates data (num_gates):")
        print(gatesBrussels.head())

        print("\nFlight_No:", Flight_No)
        print("Gate_No:", Gate_No)

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

    return flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates, Flight_No, Gate_No, ETA, ETD, P_preferences, \
        flights_to_activities, activities_to_flights, num_activities, U_successor, M_validGate, shadow_constraints, no_towable_flights, gates_to_indices, indices_to_gates



