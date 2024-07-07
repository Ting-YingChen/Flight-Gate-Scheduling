import pandas as pd
import datetime

# Data Import Functions
def import_data(local_path, EstimatedOrReal):
    # Flights
    flights = pd.read_excel(local_path, sheet_name='EBBR - Flights', usecols='A:AV', header=1, index_col=0)
    num_flights = len(flights)

    # Gates
    gates = pd.read_excel(local_path, sheet_name='EBBR - Gates (data)', usecols='A:G', header=0, index_col=0)
    num_gates = len(gates)

    # T Matrix (Time Differences)
    T_timeDiff_Estim = pd.read_excel(local_path, sheet_name='EBBR - Tmatrix (estimated)', usecols='A:PK', header=0, index_col=0)
    T_timeDiff_Real = pd.read_excel(local_path, sheet_name='EBBR - Tmatrix (real)', usecols='A:OD', header=0, index_col=0)
    if EstimatedOrReal == "Estimated":
        T_timeDiff = T_timeDiff_Estim
        num_activities = len(T_timeDiff_Estim)
    elif EstimatedOrReal == "Real":
        T_timeDiff = T_timeDiff_Real
        num_activities = len(T_timeDiff_Real)

    # Gates Neighbours and Distances
    Gates_N = pd.read_excel(local_path, sheet_name='EBBR - Gates (next)', usecols='A:DA', header=0, index_col=0, nrows=num_gates)

    return flights, num_flights, gates, num_gates, T_timeDiff, Gates_N

# # Import data
# EstimatedOrReal = "Estimated"
# EstimatedOrReal = "Real"
# flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates = import_data(LOCAL_PATH, EstimatedOrReal)



# Processing functions for flight and gate data
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

# # Process data
# Flight_No, Gate_No, ETA, ETD = process_data(flightsBrussels, gatesBrussels)



# Preferences setup
def build_preferences_dict(flights, Is_Int, Is_LowCost, Is_Close, Flight_No, M_validGate):
    """ Builds a dictionary of flight preferences. """
    P_preferences = {}  # keys: flights, values: dictionary with keys = gate IDs, values = assigned preference
    for flight in Flight_No:
        P_preferences[flight] = {}
        for gate in M_validGate[flight]:
            F_pref = 0
            if gate == "Dum":
                F_pref -= 1000     # For dummy gate, set preference to some large <0 value
            else:
                prefForInt = flights.loc[flight, "Pref. Int"]
                BothAreInt = prefForInt == 10 and Is_Int[gate] == (1 or 2)  # If flight is INT and gate is INT or remote
                BothAreEU = prefForInt == 0 and Is_Int[gate] == (0 or 2)    # If flight is EU and gate is EU or remote
                if BothAreInt or BothAreEU:
                    # F_pref += 10     # This is not a preference, it's a constraint -> already included in M_validGate
                    pass
                if BothAreEU:
                    prefForNormal = flights.loc[flight, "Pref. EU (normal)"]
                    prefForLowCost = flights.loc[flight, "Pref. EU (low cost)"]
                    prefForClose = flights.loc[flight, "Pref. Close"]
                    BothNormal = prefForNormal == 10 and Is_LowCost[gate] == 0
                    BothLowCost = prefForLowCost == 10 and Is_LowCost[gate] == 1
                    GateIsClose = Is_Close[gate] == 1
                    if BothNormal:
                        F_pref += prefForNormal
                    elif BothLowCost:
                        F_pref += prefForLowCost
                    elif GateIsClose:
                        if prefForClose == 0:
                            F_pref -= 10    # -10 pts of preference if flight doesn't want a close gate
                        elif prefForClose == 5:
                            F_pref -= 0     # 0 pts of preference if flight is indifferent to a close gate
                        elif prefForClose == 10:
                            F_pref += 10    # +10 pts of preference if flight does want a close gate
                    elif not GateIsClose:
                        if prefForClose == 0:
                            F_pref += 10    # +10 pts of preference if flight doesn't want a close gate
                        elif prefForClose == 5:
                            F_pref -= 0     # 0 pts of preference if flight is indifferent to a close gate
                        elif prefForClose == 10:
                            F_pref -= 10    # -10 pts of preference if flight does want a close gate

            P_preferences[flight][gate] = F_pref

    return P_preferences

# # Build preferences
# P_preferences = build_preferences_dict(flightsBrussels)



# Creation of activities for each flight
def createActivitiesFromFlights_Python(Flight_No, flights):
    '''map flights to activities (arrivals, departures, parking [if possible]).
    also creates a successor dictionary udict.
    '''
    flights_to_activities = {} # keys: flight no., values: list of all activities associated with respective flight
    activities_to_flights = {} # inverse dictionary of flights_to_activities
    Udict = {}
    no_towable_flights = 0  # counts the number of flights that can theoretically be towed

    for flight in Flight_No:
        # arrival = flights.loc[flight, "ETA"]
        # departure = flights.loc[flight, "ETD"]
        arrival = flights.loc[flight, "RTA"]
        departure = flights.loc[flight, "RTD"]
        TotDelay = flights.loc[flight, "Total Delay"]
        is_turnaround = None

        # Decide whether flight is towable or not
        dep_datetime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), departure)
        arr_datetime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), arrival)
        #TotDelay_datetime = datetime.datetime.combine(datetime.datetime(2000, 1, 1), TotDelay) # Doesn't work because string?
        layover_seconds = dep_datetime - arr_datetime

        # Conditions for flight to be towable:
        C1 = layover_seconds > datetime.timedelta(seconds=3600)                     # Layover > 60min
        hours, minutes = map(int, flights.loc[flight, "Total Delay"].split(":"))
        NewTotDelay = (hours * 60 + minutes) * 60
        C2 = NewTotDelay > 1200  # Delay < 20min (avoid delaying the flight even more)
        #C2 = TotDelay_datetime > datetime.timedelta(seconds=1200)  # Delay < 20min (avoid delaying the flight even more)

        # todo: add more conditions?
        ''' How to have a conditions:
            - Towable if suggested gate (to be towed to) is not remote (int = 2) or dummy (needed?)?
            - Towable if suggested gate (to be towed to) has a higher preference by this flight?
            - Towable if -current gate assigned to-'s utilisation ratio >75%? (maybe to maximise gate utilisation and minimise personnel?)
        '''
        is_towable = C1 and C2

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

        # map activities to flights
        activities_to_flights[f"arrival_{flight}"] = flight
        activities_to_flights[f"departure_{flight}"] = flight
        if is_towable:
            activities_to_flights[f"parking_{flight}"] = flight

    num_activities = len(activities_to_flights)

    return flights_to_activities, activities_to_flights, Udict, no_towable_flights, num_activities



def createActivitiesFromFlights_VBA(T_timeDiff, flights, EstimatedOrReal):
    '''map flights to activities (arrivals, departures, parking [if possible]).
    also creates a successor dictionary udict.
    '''
    flights_to_activities = {} # keys: flight no., values: list of all activities associated with respective flight
    activities_to_flights = {} # inverse dictionary of flights_to_activities
    Udict = {}
    no_towable_flights = 0  # counts the number of flights that can theoretically be towed

    if EstimatedOrReal == "Estimated":
        ColumnCheckTurnaround = 35
    elif EstimatedOrReal == "Real":
        ColumnCheckTurnaround = 46

    myActivities = T_timeDiff.columns.tolist()  # Get all activities
    myFlightsList = sorted(set([int(e[4:]) for e in myActivities])) # activities from the excel start with arr_, dep_ or par_ -> remove the 1st four characters'

    for flight in myFlightsList:
        FlightIsTurnAround = flights.iloc[flight-1, ColumnCheckTurnaround]
        is_towable = FlightIsTurnAround == "No"

        # map flights to activities
        flights_to_activities[flight] = [f"arr_{flight}", f"dep_{flight}"]
        Udict[f"dep_{flight}"] = 0    # departures activity has no successor
        if is_towable:
            no_towable_flights += 1
            flights_to_activities[flight].append(f"parking_{flight}")
            Udict[f"arrival_{flight}"] = f"parking_{flight}"
            Udict[f"parking_{flight}"] = f"departure_{flight}"
        else:
            Udict[f"arr_{flight}"] = f"dep_{flight}"

        # map activities to flights
        activities_to_flights[f"arr_{flight}"] = flight
        activities_to_flights[f"dep_{flight}"] = flight
        if is_towable:
            activities_to_flights[f"par_{flight}"] = flight

    num_activities = len(myActivities)

    return flights_to_activities, activities_to_flights, Udict, no_towable_flights, num_activities


# # Create flight activities
#flights_to_activities, activities_to_flights, U_successor = createActivitiesFromFlights_Python(Flight_No, flights)
#EstimatedOrReal = "Estimated"
#EstimatedOrReal = "Real"
#flights_to_activities, activities_to_flights, U_successor = createActivitiesFromFlights_VBA(T_timeDiff, flights, EstimatedOrReal)



# # Successor function and gate assignments
# def build_Udict(Flight_No):
#     """ Builds a successor function dictionary. """
#     return {flight: [3 * flight -2, 3 * flight, 0] for flight in Flight_No}

def build_Mdict(AC_size, Pref_Int, Max_Wingspan, Is_Int, Flight_No, Gate_No):
    Mdict = {}
    for flight in Flight_No:
        valid_gates = [gate for gate in Gate_No if AC_size.loc[flight] <= Max_Wingspan.loc[gate] and (Pref_Int[flight] / 10 == Is_Int.loc[gate] or Is_Int.loc[gate] == 2)]
        Mdict[flight] = valid_gates + ['Dum']  # Include dummy gate

    return Mdict

# # Setup M dictionary
# U_successor = build_Udict(Flight_No)
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

# # Build shadow constraints
# shadow_constraints = build_ShadowConstraints(Flight_No, ETA, ETD, M_validGate, Gates_N)

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
def createInputData(local_path, check_output, EstimatedOrReal):
    # Create all needed data structured required as input for the MIP or the heuristic.
    flights, num_flights, gates, num_gates, T_timeDiff, Gates_N = import_data(local_path, EstimatedOrReal)

    # Process data
    Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close = process_data(flights, gates)

    # Create activities and generate successor function
    #flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities = createActivitiesFromFlights_Python(Flight_No, flights)
    flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities = createActivitiesFromFlights_VBA(T_timeDiff, flights, EstimatedOrReal)

    # Create feasible gate dictionary M
    M_validGate = build_Mdict(flights['AC size (m)'], flights["Pref. Int"], gates['Max length (m)'],
        gates['International'], Flight_No, Gate_No)

    # Build preferences
    P_preferences = build_preferences_dict(flights, gates['International'], gates['Low cost'],
        gates["Close"], Flight_No, M_validGate)

    # Build shadow constraints
    shadow_constraints = build_ShadowConstraints(Flight_No, ETA, ETD, M_validGate, Gates_N)

    # map gate IDs to indices
    gates_to_indices, indices_to_gates = mapGatesToIndices(Gates_N)

    # if desired: print some sample data from the results
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


# Configurations for data import
LOCAL_PATH_TingYing = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'
LOCAL_PATH_Arthur = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'
LOCAL_PATH_Andreas = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels copy.xlsm'
LOCAL_PATH = LOCAL_PATH_Arthur

(flights, num_flights, gates, num_gates, T_timeDiff, Gates_N,
 Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close,
 P_preferences,
 flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities,
 M_validGate,
 shadow_constraints,
 gates_to_indices, indices_to_gates) = createInputData(LOCAL_PATH, False, "Real")