# Example Inputs with Updated Constraints for Dummy Gate

# Define flights and gates
flights = ['Flight 1', 'Flight 2', 'Flight 3', 'Flight 4', 'Flight 5', 'Flight 6']
num_flights = len(flights)  # Number of flights

gates = ['Gate 1', 'Gate 2', 'Gate 3', 'Dummy Gate']
num_gates = len(gates)  # Number of real gates plus one dummy gate for overflow

# todo: note: right here you can use lists. Once you transfer flights to activities, you should use dictionaries!

# Define time differences indicating when one flight can sequentially follow another
# We have this :)
T = [
    [0, 15, -10, 25, 30, 20],   # Flight 1
    [15, 0, 20, -5, 25, 30],    # Flight 2
    [-10, 20, 0, 30, -5, 25],   # Flight 3
    [25, -5, 30, 0, 20, -10],   # Flight 4
    [30, 25, -5, 20, 0, 30],    # Flight 5
    [20, 30, 25, -10, 30, 0]    # Flight 6
]

# Updated preferences for each flight regarding each gate
# Dictionary better!!!
P = [
    [60, 50, 40, 45],  # Flight 1 now has a better preference for the Dummy Gate
    [70, 60, 50, 55],  # Flight 2
    [30, 80, 60, 65],  # Flight 3
    [40, 30, 70, 35],  # Flight 4
    [50, 40, 20, 45],  # Flight 5
    [60, 45, 35, 50]   # Flight 6
]

# todo: successor function must have EXACTLY one entry for each flight
U = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # Successor function for each flight and gate

# Specify valid gate assignments for each flight (inclusive of the Dummy Gate without capacity constraints)
# This later will be dictionary too !!!
# always put dummy gate at the end
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
    (0, 2, 2, 3),  # Flight 1 cannot be at Gate 2 while Flight 3 is at Gate 3 due to proximity constraints
    (1, 1, 4, 2),  # Flight 2 cannot be at Gate 2 while Flight 5 is at Gate 3 due to maintenance at Gate 2
    (1, 3, 4, 3),  # Flight 2 at Gate 4 and Flight 5 at Gate 4 are also not possible if Gate 4 is under maintenance
]