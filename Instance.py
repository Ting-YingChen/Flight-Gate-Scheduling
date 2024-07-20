import pandas as pd
import datetime

def import_data(local_path, EstimatedOrReal):
    # Flights
    flights = pd.read_excel(local_path, sheet_name='EBBR - Flights', usecols='A:AV', header=1, index_col=0)
    num_flights = len(flights)

    # Gates
    gates = pd.read_excel(local_path, sheet_name='EBBR - Gates (data)', usecols='A:G', header=0, index_col=0)
    num_gates = len(gates)

    # T Matrix (Time Differences)
    # Regular instance
    T_timeDiff_Estim = pd.read_excel(local_path, sheet_name='EBBR - Tmatrix (estimated)', usecols='A:PK', header=0, index_col=0)
    T_timeDiff_Real = pd.read_excel(local_path, sheet_name='EBBR - Tmatrix (real)', usecols='A:OD', header=0, index_col=0)
    if EstimatedOrReal == "Estimated":
        T_timeDiff = T_timeDiff_Estim
    elif EstimatedOrReal == "Real":
        T_timeDiff = T_timeDiff_Real

    # Smaller instance (1/3rd of the flights)
    # T_timeDiff_Estim = pd.read_excel(local_path, sheet_name='EBBR - Tmatrix (estimated)', usecols='A:EP', header=0, index_col=0)
    # T_timeDiff_Real = pd.read_excel(local_path, sheet_name='EBBR - Tmatrix (real)', usecols='A:ED', header=0, index_col=0)
    # if EstimatedOrReal == "Estimated":
    #     T_timeDiff = T_timeDiff_Estim
    # elif EstimatedOrReal == "Real":
    #     T_timeDiff = T_timeDiff_Real

    # Gates Neighbours and Distances
    Gates_N = pd.read_excel(local_path, sheet_name='EBBR - Gates (next)', usecols='A:DA', header=0, index_col=0, nrows=num_gates)

    return flights, num_flights, gates, num_gates, T_timeDiff, Gates_N

def process_data(flights, gates):
    # Flight data
    Flight_No = flights.index.tolist()          # Given indices
    ETA = flights['ETA']                        # Estimated Times of Arrivals
    ETD = flights['ETD']                        # Estimated Times of Departure
    RTA = flights['RTA']                        # Real Times of Arrivals
    RTD = flights['RTD']                        # Real Times of Departure
    AC_size = flights['AC size (m)']

    # Gate data
    Gate_No = [str(x) for x in gates.index]     # List of STRINGS (E.g. gate "140L" cannot be converted to int)
    Max_Wingspan = gates['Max length (m)']      # Max wingspan allowed on that gate
    Is_Int = gates['International']             # 1 if international,   0 if not, 2 if dummy gate
    Is_LowCost = gates['Low cost']              # 1 if low cost,        0 if not, 2 if dummy gate
    Is_Close = gates['Close']                   # 1 if close,           0 if not, 2 if dummy gate

    return Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close

def build_preferences_dict(flights, Is_Int, Is_LowCost, Is_Close, Flight_No, M_validGate):
    """ Builds a dictionary of flight preferences. """
    P_preferences = {}  # keys: flights, values: dictionary with keys = gate IDs, values = assigned preference
    for flight in Flight_No:
        P_preferences[flight] = {}
        for gate in M_validGate[flight]:
            g_pref = 0
            if gate == "Dum":
                g_pref -= 1000     # For dummy gate, set preference to some large <0 value
            else:
                prefForInt = flights.loc[flight, "Pref. Int"]
                BothAreInt = prefForInt == 10 and Is_Int[gate] == (1 or 2)  # If flight is INT and gate is INT or remote
                BothAreEU = prefForInt == 0 and Is_Int[gate] == (0 or 2)    # If flight is EU and gate is EU or remote
                if BothAreInt or BothAreEU:
                    g_pref += 10     # Already included in M_validGate, but the preference still increases
                    pass
                if BothAreEU:
                    prefForNormal = flights.loc[flight, "Pref. EU (normal)"]
                    prefForLowCost = flights.loc[flight, "Pref. EU (low cost)"]
                    prefForClose = flights.loc[flight, "Pref. Close"]
                    BothNormal = prefForNormal == 10 and Is_LowCost[gate] == 0
                    BothLowCost = prefForLowCost == 10 and Is_LowCost[gate] == 1
                    GateIsClose = Is_Close[gate] == 1
                    if BothNormal:
                        g_pref += prefForNormal
                    elif BothLowCost:
                        g_pref += prefForLowCost
                    elif GateIsClose:
                        if prefForClose == 0:
                            g_pref -= 10    # -10 pts of preference if flight doesn't want a close gate
                        elif prefForClose == 5:
                            g_pref -= 0     # 0 pts of preference if flight is indifferent to a close gate
                        elif prefForClose == 10:
                            g_pref += 10    # +10 pts of preference if flight does want a close gate
                    elif not GateIsClose:
                        if prefForClose == 0:
                            g_pref += 10    # +10 pts of preference if flight doesn't want a close gate
                        elif prefForClose == 5:
                            g_pref -= 0     # 0 pts of preference if flight is indifferent to a close gate
                        elif prefForClose == 10:
                            g_pref -= 10    # -10 pts of preference if flight does want a close gate

            P_preferences[flight][gate] = g_pref

    return P_preferences

def createActivitiesFromFlights_VBA(T_timeDiff, flights, EstimatedOrReal):
    '''map flights to activities (arrivals, departures, parking [if possible]).
    also creates a successor dictionary udict.
    '''
    flights_to_activities = {} # keys: flight no., values: list of all activities associated with respective flight
    activities_to_flights = {} # inverse dictionary of flights_to_activities
    Udict = {}
    no_towable_flights = 0  # counts the number of flights that can theoretically be towed

    if EstimatedOrReal == "Estimated":
        ColumnCheckTurnaround = 37-1-1      # Column AK is the 37th column, -1 because column 1 = indices, -1 because .iloc start from 0
    elif EstimatedOrReal == "Real":
        ColumnCheckTurnaround = 48-1-1      # Column AV is the 48th column, -1 because column 1 = indices, -1 because .iloc start from 0

    myActivities = T_timeDiff.columns.tolist()  # Get all activities
    myFlightsList = flights.index.tolist()

    for flight in myFlightsList:
        FlightIsTurnAround = flights.iloc[flight-1, ColumnCheckTurnaround]
        is_towable = FlightIsTurnAround == "No"

        # map flights to activities
        flights_to_activities[flight] = [f"arr_{flight}", f"dep_{flight}"]
        Udict[f"dep_{flight}"] = 0    # departures activity has no successor
        if is_towable:
            no_towable_flights += 1
            flights_to_activities[flight].append(f"par_{flight}")
            Udict[f"arr_{flight}"] = f"par_{flight}"
            Udict[f"par_{flight}"] = f"dep_{flight}"
        else:
            Udict[f"arr_{flight}"] = f"dep_{flight}"

        # map activities to flights
        activities_to_flights[f"arr_{flight}"] = flight
        activities_to_flights[f"dep_{flight}"] = flight
        if is_towable:
            activities_to_flights[f"par_{flight}"] = flight

    num_activities = len(myActivities)

    return flights_to_activities, activities_to_flights, Udict, no_towable_flights, num_activities

def build_Mdict(AC_size, Pref_Int, Max_Wingspan, Is_Int, Flight_No, Gate_No):
    Mdict = {}
    for flight in Flight_No:
        valid_gates = [gate for gate in Gate_No if AC_size.loc[flight] <= Max_Wingspan.loc[gate] and (Pref_Int[flight] / 10 == Is_Int.loc[gate] or Is_Int.loc[gate] == 2)]
        # Mdict[flight] = valid_gates + ['Dum']  # Include dummy gate
        Mdict[flight] = valid_gates
    return Mdict

def build_ShadowConstraints(activities_to_flights, T_timeDiff, M_validGate, Gates_N):
    """ Constructs shadow constraints based on flight scheduling logic. """
    # preprocessing: store information on neighbouring or identical gates. Reduces runtime by >90%
    GatesAreNext = {}
    GatesAreSame = {}
    for gate_f1 in Gates_N.index:
        for gate_f2 in Gates_N.columns:
            GatesAreNext[(gate_f1, gate_f2)] = Gates_N.loc[gate_f1, gate_f2] == 1
            GatesAreSame[(gate_f1, gate_f2)] = Gates_N.loc[gate_f1, gate_f2] == -1  # Check if they are the same gates

    shadow_constraints = []
    for act1 in activities_to_flights.keys():
        for act2 in activities_to_flights.keys():
            if T_timeDiff.loc[act1, act2] < 0:      # Check if activities overlaps
                f1 = activities_to_flights[act1]    # Flight of act1
                f2 = activities_to_flights[act2]    # Flight of act2
                for gate1 in M_validGate[f1]:
                    for gate2 in M_validGate[f2]:
                        if (GatesAreNext[(gate1, gate2)] or GatesAreSame[(gate1, gate2)]) and (gate1 != 'Dum' and gate2 != 'Dum'):
                            shadow_constraints.append((act1, gate1, act2, gate2))
    return shadow_constraints

def convert_sc_to_dicts(shadow_constraints):
    '''Convert shadow constraint list into easier-to-access dictionaries.
    '''
    sc_per_act_gate_pair = {}   # { ('act1', 'gate1'): [ ('actX', 'gateY'), ('actZ', 'gateA'), ...], ('act2', 'gate2'): [...], ... }
    sc_per_gate = {}            # { 'gate1': [('act1', 'act2', 'gate1'), (...), ...], 'gate2': [...], ... }

    for (a1, g1, a2, g2) in shadow_constraints:
        # dictionary with keys = tuples of flight and gate
        if (a1, g1) not in sc_per_act_gate_pair:
            sc_per_act_gate_pair[(a1, g1)] = []
        sc_per_act_gate_pair[(a1, g1)].append((a2, g2))
        if (a2, g2) not in sc_per_act_gate_pair:
            sc_per_act_gate_pair[(a2, g2)] = []
        sc_per_act_gate_pair[(a2, g2)].append((a1, g1))

        # dictionary with keys = gates
        if g1 not in sc_per_gate:
            sc_per_gate[g1] = []
        sc_per_gate[g1].append((a1, a2, g2))
        if g2 not in sc_per_gate:
            sc_per_gate[g2] = []
        sc_per_gate[g2].append((a2, a1, g1))

    return sc_per_act_gate_pair, sc_per_gate

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

def createInputData(local_path, check_output, EstimatedOrReal):
    flights, num_flights, gates, num_gates, T_timeDiff, Gates_N = import_data(local_path, EstimatedOrReal)
    Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close = process_data(flights, gates)
    flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities = createActivitiesFromFlights_VBA(T_timeDiff, flights, EstimatedOrReal)
    M_validGate = build_Mdict(flights['AC size (m)'], flights["Pref. Int"], gates['Max length (m)'], gates['International'], Flight_No, Gate_No)
    P_preferences = build_preferences_dict(flights, gates['International'], gates['Low cost'], gates["Close"], Flight_No, M_validGate)
    shadow_constraints = build_ShadowConstraints(activities_to_flights, T_timeDiff, M_validGate, Gates_N)
    gates_to_indices, indices_to_gates = mapGatesToIndices(Gates_N)

    # if desired: print some sample data from the resultss
    if check_output:
        # Print the first few rows of the flights data to confirm correct loading and indexing
        print("First few flights data:")
        print(flights.head())

        # Print the first few rows of the gates data to verify correct loading
        print("\nFirst few gates data (num_gates):")
        print(gates.head())

        print("\nFlight_No:", Flight_No)
        print("Gate_No:", Gate_No)

        # Check a slice of the T matrix to ensure it's properly loaded
        print("\nSample of T matrix (T_timeDiff):")
        print(T_timeDiff.iloc[:5, :5])

        # Print details of the Gates Neighbours
        print("\nGates Neighbours Matrix Sample:")
        print(Gates_N.iloc[:5, :5])

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

    return (flights, num_flights, gates, num_gates, T_timeDiff, Gates_N,
            Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close,
            P_preferences,
            flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities,
            M_validGate,
            shadow_constraints,
            gates_to_indices, indices_to_gates)


if __name__ == "__main__":
    # Configurations for data import
    LOCAL_PATH_TingYing = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'
    LOCAL_PATH_Arthur = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'
    LOCAL_PATH_Andreas = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels copy.xlsm'
    LOCAL_PATH = LOCAL_PATH_Arthur

    # ONLY call function when script is directly called, not when it is imported
    (flights, num_flights, gates, num_gates, T_timeDiff, Gates_N,
     Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close,
     P_preferences,
     flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities,
     M_validGate,
     shadow_constraints,
     gates_to_indices, indices_to_gates) = createInputData(LOCAL_PATH, False, "Real")


def simulatenous_flights():
    max = 0
    maxA = ''
    for activity1 in list(activities_to_flights.keys()):
        simultaneous_flights = 0
        for activity2 in list(activities_to_flights.keys()):
            c1 = T_timeDiff.loc[activity1, activity2] < 0      # Indirectly verifies that activity2 != activity1
            fligth1 = activities_to_flights[activity1]
            flight2 = activities_to_flights[activity2]
            c2 = fligth1 != flight2
            c3 = activity1[0:2] != activity2[0:2]              # If arr_1 overlaps with arr_2 and dep_1 overlaps with dep_2, that is only 1 overlap of flights, not 2)
            if c1 and c2:
                simultaneous_flights += 1
        if simultaneous_flights > max:
            max = simultaneous_flights
            maxA = fligth1
    print("Max simul = ", max, maxA)    # Says 226, >171 ...
    return