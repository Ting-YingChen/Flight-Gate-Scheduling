import Instance
def calculate_large_negative(activities_to_flights, num_activities, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max):
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

def get_weight_matrix(num_activities, activities_to_flights, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3,
                      t_max, large_negative, gates_to_indices, indices_to_gates):
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
    for i in activities_to_flights:
        for j in activities_to_flights:
            # 1.1 If activities belong to different flights and overlap in time: assign large negative
            if T_timeDiff.loc[i, j] < 0:  # Activities overlap in time
                weights[i][j] = large_negative
                weights[j][i] = large_negative
            else:
                # 1.2 if activities do not overlap and are successors: set weight to alpha2
                if U_successor[i] == j or U_successor[j] == i:
                    weights[i][j] = alpha2
                    weights[j][i] = alpha2
                # 1.3 if activities do not overlap and do not succeed each other: set weight to -alpha3*excess buffer time#
                # <=> penalty for having not enough buffer time
                else:
                    excess_buffer_time = max(t_max - T_timeDiff.loc[i, j], 0)
                    weights[i][j] = -alpha3*excess_buffer_time
                    weights[j][i] = -alpha3*excess_buffer_time

    # 2. weights between activity and gate nodes
    for i in activities_to_flights:
        flight_i = activities_to_flights[i]
        for k in gates_to_indices:
            if k in M_validGate[flight_i]:
                weights[i][k] = alpha1 * P_preferences[flight_i][k]
                weights[k][i] = alpha1 * P_preferences[flight_i][k]
            else:
                weights[i][k] = large_negative
                weights[k][i] = large_negative

    # 3. weights between gates (large negative)
    for g1 in gates_to_indices:  # Change to num_gates if it works
        for g2 in gates_to_indices:
            weights[g1][g2] = large_negative
            weights[g2][g1] = large_negative

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
    weights = get_weight_matrix(num_activities, activities_to_flights, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3,
                          t_max, large_negative, gates_to_indices, indices_to_gates)


    print(f"Here: {weights}")

    return

if __name__ == "__main__":
    TryThingsOut()

