import Instance
def calculate_large_negative(activities_to_flights, num_activities, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max):
    """
        Calculate the large negative value used to adjust solution feasibilities in optimization models.

        Parameters:
            num_flights (int): Total number of flights, starting from 1.
            T_timeDiff (list of lists): Matrix of time differences between flights, indexed from 0.
            P_preferences (dict): Dictionary mapping each flight number (starting from 1) to their gate preferences scores.
            M_validGate (dict): Dictionary mapping each flight number (starting from 1) to a list of valid gate identifiers.
            alpha1, alpha2, alpha3 (int): Weight factors for preferences, tow rewards, and penalties.
            t_max (int): Maximum time buffer allowed between flights.

        Returns:
            int: The calculated large negative value to be used in optimization constraints.
        """

    # Calculate the minimum possible alpha1 preferences by choosing the least preferred gate (alpha1)
    min_preferences = []
    for activity in activities_to_flights:
        flight = activities_to_flights[activity]
        if activity in P_preferences and flight in M_validGate:
            flight_min_pref = min(
                alpha1 * P_preferences[flight][gate] for gate in M_validGate[flight] if gate in P_preferences[activity])
            min_preferences.append(flight_min_pref)
        # print(f"Flight {flight}: Min preference = {flight_min_pref}")
    total_min_preferences = sum(min_preferences)
    print(f"Total minimum preferences: {total_min_preferences}")

    # Calculate the maximum possible alpha2 rewards assuming every flight needs a tow (alpha2)
    max_tow_rewards = no_towable_flights * alpha2
    print(f"Max tow rewards (all flights): {max_tow_rewards}")

    # Calculate the maximum possible alpha3 penalties when all flights have the least buffer time (alpha3)
    max_buffer_penalties = 0
    for i in activities_to_flights:
        for j in activities_to_flights:
            if i != j and i in T_timeDiff and j in T_timeDiff[i]:
                if T_timeDiff[i][j] < t_max and T_timeDiff[i][j] > 0:
                    penalty_value = alpha3 * (t_max - T_timeDiff[i][j])
                    max_buffer_penalties += penalty_value
                    # print(f"Buffer penalty between flight {i} and {j}: {penalty_value}")
    print(f"Total buffer penalties: {max_buffer_penalties}")

    # Sum all components to find the upper bound of any feasible solution's objective value
    upper_bound = total_min_preferences + max_tow_rewards + max_buffer_penalties
    print(f"Calculated upper bound: {upper_bound}")

    # Set large_negative to a value slightly larger than the calculated upper bound
    large_negative = -1 * (upper_bound + 1)
    print(f"Large negative value: {large_negative}")
    return large_negative

# Example usage
# large_negative = calculate_large_negative(Flight_No, num_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
# print("Recommended large_negative value:", large_negative)


def get_weight_matrix2(num_flights, num_activities, T_timeDiff, P_preferences, M_validGate,
                       alpha1, alpha3, t_max, large_negative,
                       activities_to_flights):
    # Initialize the edge weights matrix
    # vertices = num_flights + num_gates - 1  # (5)
    vertices = num_activities
    weights = [[0] * vertices for _ in range(vertices)]

    # Iterate through pairs of activities to set the weights based on temporal overlaps
    for i in range(num_activities):
        activity_i = list(activities_to_flights.keys())[i]
        flight_i = activities_to_flights[activity_i]
        for j in range(i+1, num_activities):
            activity_j = list(activities_to_flights.keys())[j]
            flight_j = activities_to_flights[activity_j]
            buffer_time = T_timeDiff.iloc[i, j]

            # 1. if buffer time negative: activities overlap -> set edge weight to -large number
            # If activities belong to different flights and overlap in time: assign large negative
            if flight_i != flight_j and buffer_time < 0:  # Activities overlap in time
                weights[i][j] = large_negative
            elif buffer_time >= 0:
                weights[i][j] = -alpha3 * max(t_max - buffer_time, 0)  # Buffer time difference


    '''
    # Populate the weights matrix based on given rules (6)
    for i in range(len(activities_to_flights) - 1):  # Using zero-based indices
        for j in range(i+1, len(activities_to_flights)):
            if i != j:
                if T_timeDiff[i][j] < 0:  # Activities overlap in time
                    weights[i][j] = large_negative
                elif j in U_successor[i]:  # Saving a tow (assuming U_successor[i] gives a list of successor flights)
                    weights[i][j] = alpha2
                else:
                    buffer_time = T_timeDiff[i][j]
                    if buffer_time >= 0:
                        weights[i][j] = -alpha3 * max(t_max - buffer_time, 0)  # Buffer time difference
    '''

    # Weights for flight to gate assignments (7)
    for i in range(num_activities):
        activity_i = list(activities_to_flights.keys())[i]
        flight_i = activities_to_flights[activity_i]

        for j in range(num_flights, vertices):
            gate_index = j - num_flights  # Mapping index to gate name
            if gate_index in M_validGate[flight_i]:
                weights[i][j] = alpha1 * P_preferences[flight_i][gate_index]
            else:
                weights[i][j] = large_negative

    # Gates cannot be in the same clique (8)
    for i in range(num_flights, vertices):
        for j in range(i + 1, num_flights, vertices):
            weights[i][j] = large_negative

    return vertices, weights



def get_weight_matrix3(num_activities, activities_to_flights, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3,
                      t_max, large_negative, gates_to_indices, indices_to_gates):
    """
    Generate a weight matrix for activities, considering interactions between activities and gates.
    """

    # 0. initialize empty weight matrix
    weights = {}
    for node_i in list(activities_to_flights.keys()) + list(gates_to_indices.keys()):
        weights[node_i] = {}
        for node_j in list(activities_to_flights.keys()) + list(gates_to_indices.keys()):
            if node_i == node_j:
                weights[node_i][node_j] = 0
            else:
                weights[node_i][node_j] = None

    # 1. create edges between activity nodes
    for i in range(num_activities - 1):
        activity_i = list(activities_to_flights.keys())[i]
        flight_i = activities_to_flights[activity_i]
        for j in range(i+1, num_activities):
            activity_j = list(activities_to_flights.keys())[j]
            flight_j = activities_to_flights[activity_j]
            # 1.1 If activities belong to different flights and overlap in time: assign large negative
            if T_timeDiff.iloc[i, j] < 0:  # Activities overlap in time
                weights[activity_i][activity_j] = large_negative
                weights[activity_j][activity_i] = large_negative
            else:
                # 1.2 if activities do not overlap and are successors: set weight to alpha2
                if U_successor[activity_i] == activity_j or U_successor[activity_j] == activity_i:
                    weights[activity_i][activity_j] = alpha2
                    weights[activity_j][activity_i] = alpha2
                # 1.3 if activities do not overlap and do not succeed each other: set weight to -alpha3*excess buffer time
                else:
                    excess_buffer_time = max(t_max - T_timeDiff.iloc[i, j], 0)
                    weights[activity_i][activity_j] = excess_buffer_time
                    weights[activity_j][activity_i] = excess_buffer_time

    # 2. weights between activity and gate nodes
    for i in range(num_activities):
        activity_i = list(activities_to_flights.keys())[i]
        flight_i = activities_to_flights[activity_i]
        for j in indices_to_gates:
            gate_j = indices_to_gates[j]
            if gate_j in M_validGate[flight_i]:
                weights[activity_i][gate_j] = alpha1 * P_preferences[flight_i][gate_j]
                weights[gate_j][activity_i] = alpha1 * P_preferences[flight_i][gate_j]
            else:
                weights[activity_i][gate_j] = large_negative
                weights[gate_j][activity_i] = large_negative

    # 3. weights between gates (large negative)
    for i in range(len(gates_to_indices) - 1):  # Change to num_gates if it works
        gate_i = list(gates_to_indices.keys())[i]
        for j in range(i, len(gates_to_indices)):
            gate_j = list(gates_to_indices.keys())[j]
            weights[gate_i][gate_j] = large_negative
            weights[gate_j][gate_i] = large_negative

    return weights




# Example usage:
def TryThingsOut():
    alpha1 = 1  # Preference scaling factor
    alpha2 = 20  # Reward for avoiding tows
    alpha3 = 100  # Penalty scaling factor for buffer time deficits
    t_max = 30
    local_path = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'
    (flights, num_flights, gates, num_gates, T_timeDiff, Gates_N,
         Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close,
         P_preferences,
         flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities,
         M_validGate,
         shadow_constraints,
         gates_to_indices, indices_to_gates) = Instance.createInputData(local_path, False, "Real")
    large_negative = calculate_large_negative(activities_to_flights, num_activities, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
    weights = get_weight_matrix3(num_activities, activities_to_flights, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3,
                          t_max, large_negative, gates_to_indices, indices_to_gates)


    print(f"Here: {weights}")

    return

TryThingsOut()

