# from instance_TYorganised import Flight_No, num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max

import numpy as np
def calculate_large_negative(num_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max):
    """
    Calculate the large negative value used to adjust solution feasibilities in optimization models.

    Parameters:
        num_flights (int): Total number of flights.
        T_timeDiff (dict): Dictionary of time differences between flights, indexed from 0.
        P_preferences (dict): Dictionary mapping each flight number (starting from 0) to their gate preferences scores.
        M_validGate (dict): Dictionary mapping each flight number (starting from 0) to a set of valid gate identifiers.
        alpha1, alpha2, alpha3 (float): Weight factors for preferences, tow rewards, and penalties.
        t_max (int): Maximum time buffer allowed between flights.

    Returns:
        int: The calculated large negative value to be used in optimization constraints.
    """
    # Calculate the minimum possible alpha1 preferences by choosing the least preferred gate (alpha1)
    min_preferences = []
    for flight in range(num_flights):
        # Ensure that the flight index matches the dictionary keys which should start from 0
        if flight in P_preferences:
            valid_gates = M_validGate[flight]
            flight_min_pref = min(alpha1 * P_preferences[flight][gate] for gate in valid_gates if gate < len(P_preferences[flight]))
            min_preferences.append(flight_min_pref)

    total_min_preferences = sum(min_preferences)
    print(f"Total minimum preferences: {total_min_preferences}")

    # Calculate the maximum possible alpha2 rewards assuming every flight needs a tow (alpha2)
    max_tow_rewards = num_flights * alpha2
    print(f"Max tow rewards (all flights): {max_tow_rewards}")

    # Calculate the maximum possible alpha3 penalties when all flights have the least buffer time (alpha3)
    max_buffer_penalties = 0
    for i in range(num_flights):
        for j in range(num_flights):
            if i != j:
                buffer_time = T_timeDiff.get((i, j), np.inf)  # Use a large default if not specified
                if buffer_time < t_max:
                    penalty_value = alpha3 * (t_max - buffer_time)
                    max_buffer_penalties += penalty_value

    print(f"Total buffer penalties: {max_buffer_penalties}")

    # Sum all components to find the upper bound of any feasible solution's objective value
    upper_bound = total_min_preferences + max_tow_rewards + max_buffer_penalties
    print(f"Calculated upper bound: {upper_bound}")

    # Set large_negative to a value slightly larger than the calculated upper bound
    large_negative = -1 * (upper_bound + 1)
    print(f"Large negative value: {large_negative}")
    return large_negative

def get_weight_dict(num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative):
    vertices = num_flights + num_gates - 1  # (5)
    weights = {}

    # Flight-to-flight interactions (6)
    for i in range(num_flights):  # Using zero-based indices
        for j in range(num_flights):
            if i != j:
                key = (i, j)
                if T_timeDiff.get((i, j), 0) < 0:
                    weights[key] = large_negative
                else:
                    buffer_time = T_timeDiff.get((i, j), np.inf)  # Assume no overlap if not specified
                    if buffer_time < t_max:
                        weights[key] = -alpha3 * (t_max - buffer_time)
                    else:
                        weights[key] = 0  # No penalty if buffer is adequate

                # Check if j is a successor of i to possibly avoid a tow
                if U_successor[i] == j:
                    weights[key] += alpha2

    # Flight-to-gate assignments (7)
    for i in range(num_flights):
        for gate in range(num_gates):  # Gates indexed from 0 to num_gates-1
            key = (i, num_flights + gate)
            if gate in M_validGate[i]:
                if gate < len(P_preferences[i]):  # Check if gate index is within the list bounds
                    weights[key] = alpha1 * P_preferences[i][gate]
                else:
                    weights[key] = large_negative  # Handle dummy gate if it's out of bounds
            else:
                weights[key] = large_negative

    # Gates cannot be in the same clique (8)
    for i in range(num_flights, vertices):
        for j in range(i, vertices):
            if i != j:
                key = (i, j)
                weights[key] = large_negative

    # Handle shadow constraints by imposing infinite penalties
    for (f1, g1, f2, g2) in shadow_constraints:
        weights[(f1, num_flights + g1), (f2, num_flights + g2)] = large_negative

    return vertices, weights

# Dictionary-based data
num_flights = 4
num_gates = 3
P_preferences = {
    0: [10, 20, 30],
    1: [20, 30, 10],
    2: [30, 10, 20],
    3: [10, 30, 20]
}
U_successor = {0: 1, 1: 2, 2: 3, 3: 0}
T_timeDiff = {
    (0, 0): 0, (0, 1): 2, (0, 2): -1, (0, 3): -1,
    (1, 0): -1, (1, 1): 0, (1, 2): 3, (1, 3): -1,
    (2, 0): -1, (2, 1): -1, (2, 2): 0, (2, 3): 4,
    (3, 0): 1, (3, 1): -1, (3, 2): -1, (3, 3): 0
}
M_validGate = {0: {0, 1, 3},
               1: {1, 2, 3},
               2: {0, 2, 3},
               3: {1, 3}}

# Other parameters remain unchanged
shadow_constraints = [
    (0, 0, 1, 0),  # Flight 0 and Flight 1 cannot both use Gate 0.
    (1, 2, 2, 2),  # Flight 1 and Flight 2 cannot both use Gate 2.
    (2, 1, 3, 1)   # Flight 2 and Flight 3 cannot both use Gate 1.
]
t_max = 5
alpha1, alpha2, alpha3 = 1, 0.5, 0.2

'''
# Example usage
large_negative = calculate_large_negative(num_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
print("Recommended large_negative value:", large_negative)

vertices, weights = get_weight_dict(num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative)
print("vertices:", vertices)
print("weights:", weights)
print("Sample weights matrix keys:", list(weights.keys())[:10])
print("Sample weights matrix values:", [weights[key] for key in list(weights.keys())[:10]])
'''