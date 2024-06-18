# Example Inputs with Updated Constraints for Dummy Gate

# Define flights and gates
flights = ['Flight 1', 'Flight 2', 'Flight 3', 'Flight 4', 'Flight 5', 'Flight 6']
num_flights = len(flights)  # Number of flights

gates = ['Gate 1', 'Gate 2', 'Gate 3', 'Dummy Gate']
num_gates = len(gates)  # Number of real gates plus one dummy gate for overflow

# Define time differences indicating when one flight can sequentially follow another
T = [
    [0, 15, -10, 25, 30, 20],   # Flight 1
    [15, 0, 20, -5, 25, 30],    # Flight 2
    [-10, 20, 0, 30, -5, 25],   # Flight 3
    [25, -5, 30, 0, 20, -10],   # Flight 4
    [30, 25, -5, 20, 0, 30],    # Flight 5
    [20, 30, 25, -10, 30, 0]    # Flight 6
]

# Updated preferences for each flight regarding each gate, improving the attractiveness of the Dummy Gate
P = [
    [60, 50, 40, 45],  # Flight 1 now has a better preference for the Dummy Gate
    [70, 60, 50, 55],  # Flight 2
    [30, 80, 60, 65],  # Flight 3
    [40, 30, 70, 35],  # Flight 4
    [50, 40, 20, 45],  # Flight 5
    [60, 45, 35, 50]   # Flight 6
]

U = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # Successor function for each flight and gate

# Specify valid gate assignments for each flight (inclusive of the Dummy Gate without capacity constraints)
M = [
    [0, 1, 2, 3],    # Flight 1 can go to any gate including Dummy
    [0, 1, 2, 3],    # Flight 2
    [0, 1, 2, 3],    # Flight 3
    [0, 1, 2, 3],    # Flight 4
    [0, 1, 2, 3],    # Flight 5
    [0, 1, 2, 3]     # Flight 6
]

alpha1 = 1  # Preference scaling factor
alpha2 = 5   # Reward for avoiding tows
alpha3 = 50  # High penalty scaling factor for buffer time deficits

t_max = 30

# Shadow constraints to ensure operational compliance
'''Feedback 12.06.:
Any shadow constraint (i,k,j,l) with k = l (i.e. same gate) is trivial, as this is just a special case
of the temporal requirement "two simultaneous flights can never be assigned to the same gate".
Shadow constraints can only apply to pairs (i,j) of flights i and j if they have a temporal overlap, i.e. they are at the
airport at the same time.
An example for a realistic shadow constraint could be e.g. (0,0,1,1), meaning that flight 0 can not be parked at gate 0 while
flight 1 is parked at gate 1.
'''
shadow_constraints = [
    (0, 2, 2, 2),  # Flight 1 cannot be at Gate 3 while Flight 3 is at Gate 3 due to proximity constraints
    (1, 1, 4, 2),  # Flight 2 cannot be at Gate 2 while Flight 5 is at Gate 3 due to maintenance at Gate 2
    (1, 3, 4, 3),  # Flight 2 at Gate 4 and Flight 5 at Gate 4 are also not possible if Gate 4 is under maintenance
]


def calculate_large_negative(num_flights, T, P, U, M, alpha1, alpha2, alpha3, t_max):
    # Min possible alpha1 preferences (choosing least preferred gate)
    min_preferences = sum(min(alpha1 * P[i][g] for g in M[i]) for i in range(num_flights))

    # Max possible alpha2 rewards (every flight needing a tow)
    max_tow_rewards = sum(alpha2 for _ in range(num_flights))

    # Max possible alpha3 penalties (all flights have the least buffer time)
    max_buffer_penalties = 0
    for i in range(num_flights):
        for j in range(num_flights):
            if i != j and T[i][j] < t_max:
                max_buffer_penalties += -alpha3 * (t_max - T[i][j])

    # Summing all components to find the upper bound of any feasible solution's objective value
    upper_bound = max_tow_rewards + min_preferences + max_buffer_penalties

    # Setting large_negative to a bit more than the calculated upper bound
    large_negative = upper_bound + 1
    return large_negative


# Example usage
# large_negative = calculate_large_negative(num_flights, T, P, U, M, alpha1, alpha2, alpha3, t_max)
# print("Recommended large_negative value:", large_negative)


def get_weight_matrix(num_flights, num_gates, T, P, U, M, alpha1, alpha2, alpha3, t_max, large_negative):
    # Initialize the edge weights matrix
    vertices = num_flights + num_gates - 1  # (5)
    weights = [[0] * vertices for _ in range(vertices)]
    # large_negative = calculate_large_negative(num_flights, T, P, U, M, alpha1, alpha2, alpha3, t_max)
    '''Feedback 12.06.:
    Sometimes, using very large numbers introduces numerical instability in following calculations and/or increase runtime.
    Instead, you could set the value large_negative to be equal to some upper bound to the objective value of any feasible
    solution plus +1. For this, try to maximize all components of the objective function (->all flights need to be towed,
    gate with the lowest preference is chosen for each flight, buffer time is minimal for all flights).
    '''

    # Populate the weights matrix based on given rules (6)
    for i in range(num_flights):
        for j in range(num_flights):
            if j < num_flights:  # Interaction between flights
                if i != j:
                    if T[i][j] < 0:  # Activities overlap in time
                        weights[i][j] = large_negative
                    elif U[i] == j or U[j] == i:  # Saving a tow
                        weights[i][j] = alpha2
                    else:
                        weights[i][j] = -alpha3 * max(t_max - T[i][j], 0)  # Buffer time difference

            # Weights for flight to gate assignments (7)
            else:
                gate_index = j - num_flights
                if gate_index in M[i]:
                    weights[i][j] = alpha1 * P[i][j - num_flights]
                else:
                    weights[i][j] = large_negative
    '''
    # Why do I need to include gates in to weights matrix?
    '''
    # Gates cannot be in the same clique (8)
    for i in range(num_flights, vertices):
        for j in range(num_flights, vertices):
            weights[i][j] = large_negative

    return vertices, weights


# Example usage:
# vertices, weights = get_weight_matrix(num_flights, num_gates, T, P, U, M, alpha1, alpha2, alpha3, t_max)
# print("vertices: ", vertices)
# print("weights: ", weights)

