# from instance_TYorganised import Flight_No, num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max

def calculate_large_negative(Flight_No, num_flights, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max):
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
    for flight in Flight_No: # Flight_No starts from 1
        flight_min_pref = min(alpha1 * P_preferences[flight][gate] for gate in M_validGate[flight])
        min_preferences.append(flight_min_pref)
        # print(f"Flight {flight}: Min preference = {flight_min_pref}")
    total_min_preferences = sum(min_preferences)
    print(f"Total minimum preferences: {total_min_preferences}")

    # Calculate the maximum possible alpha2 rewards assuming every flight needs a tow (alpha2)
    max_tow_rewards = no_towable_flights * alpha2
    print(f"Max tow rewards (all flights): {max_tow_rewards}")

    # Calculate the maximum possible alpha3 penalties when all flights have the least buffer time (alpha3)
    max_buffer_penalties = 0
    for i in Flight_No:
        for j in Flight_No:
            if i != j:
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


def get_weight_matrix(Flight_No, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative,
                      flights_to_activities, activities_to_flights):
    # Initialize the edge weights matrix
    num_flights = len(Flight_No)
    vertices = num_flights + num_gates - 1  # (5)

    weights = [[0] * vertices for _ in range(vertices)]

    for i in range(len(activities_to_flights) - 1):
        activity_i = list(activities_to_flights.keys())[i]
        flight_i = activities_to_flights[activity_i]
        for j in range(i+1, len(activities_to_flights)):
            activity_j = list(activities_to_flights.keys())[j]
            flight_j = activities_to_flights[activity_j]

            # 1. if buffer time negative: activities overlap -> set edge weight to -large number
            # todo


            # If activities belong to different flights and overlap in time: assign large negative
            if flight_i != flight_j and T_timeDiff[flight_i][flight_j] < 0:  # Activities overlap in time
                weights[activity_i][activity_j] = large_negative


            else:
                buffer_time = T_timeDiff[i][j]
                if buffer_time >= 0:
                    weights[i][j] = -alpha3 * max(t_max - buffer_time, 0)  # Buffer time difference


    # Populate the weights matrix based on given rules (6)
    for i in Flight_No:  # Using zero-based indices
        for j in Flight_No:
            if i != j:
                if T_timeDiff[i][j] < 0:  # Activities overlap in time
                    weights[i][j] = large_negative
                elif j in U_successor[i]:  # Saving a tow (assuming U_successor[i] gives a list of successor flights)
                    weights[i][j] = alpha2
                else:
                    buffer_time = T_timeDiff[i][j]
                    if buffer_time >= 0:
                        weights[i][j] = -alpha3 * max(t_max - buffer_time, 0)  # Buffer time difference

    # Weights for flight to gate assignments (7)
    for i in Flight_No:
        for j in range(num_flights, vertices):
            gate_index = j - num_flights  # Mapping index to gate name
            if gate_index in M_validGate[i]:
                weights[i][j] = alpha1 * P_preferences[i][j - num_flights]
            else:
                weights[i][j] = large_negative

    # Gates cannot be in the same clique (8)
    for i in range(num_flights, vertices):
        for j in range(num_flights, vertices):
            weights[i][j] = large_negative

    return vertices, weights


# Example usage:
# vertices, weights = get_weight_matrix(num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative)
# print("vertices: ", vertices)
# print("Sample weights matrix section:", weights[:5][:5])

