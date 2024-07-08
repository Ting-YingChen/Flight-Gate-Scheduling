import numpy as np


def calculate_heuristic_value(i, C, D, weights, activities_to_flights, gates_to_indices):
    """ Calculate the heuristic value for moving vertex i from its current cluster C[i] to a new cluster D """
    # C = current cluster (list of all vertices of that cluster)
    # D = new (possibly empty) cluster (list of the vertices of that cluster)

    sum_weights_new_cluster = sum(weights[i][j] for j in D if j != 'Dum')
    sum_weights_current_cluster = sum(weights[i][j] for j in C if (j != i and j != 'Dum'))

    return sum_weights_new_cluster - sum_weights_current_cluster

def calculate_total_score(solution, weights):
    """ Calculate the total score of the current solution based on the weights matrix.
    Paper p.294, ultimate paragraph: "The CPP is to find an equivalence relation on V so that the sum of the edge
    weights of all vertices IN RELATION is maximized. This is equivalent to finding a partition of V into cliques,
    i.e., a vertex subset, so that the sum of the edge weights WITHIN the cliques is maximized. "
    """
    score = 0
    for cluster in solution:    # cluster or clique
        clusterActivities = solution[cluster]
        score += sum(weights[i][j] for i in clusterActivities for j in clusterActivities if i != j)

    return score

def get_gate_of_activity(i, solution):
    gate_of_i = 'No gate found'
    for cluster in solution:
        for activity in solution[cluster][1:]:  # solution[cluster] = ['gate', 'activity1', 'activity2', ...]
            if activity == i:
                gate_of_i = solution[cluster][0]

    return gate_of_i

def is_move_feasible(i, proposed_gate, solution, shadow_constraints, flights_to_activities, activities_to_flights):
    """
    Checks if moving flight `i` to `proposed_gate` violates any shadow constraints.
    """
    flight_of_i = activities_to_flights[i]
    gate_of_i = get_gate_of_activity(i, solution)

    for (f1, g1, f2, g2) in shadow_constraints:
        for activity_of_f1 in flights_to_activities[f1]:    # f1 has 2 or 3 activities
            for activity_of_f2 in flights_to_activities[f2]:    # f2 has ...
                gate_of_f1 = get_gate_of_activity(activity_of_f1, solution)
                gate_of_f2 = get_gate_of_activity(activity_of_f2, solution)
                condition1 = f1 == flight_of_i and g1 == proposed_gate and gate_of_f2 == g2
                condition2 = f2 == flight_of_i and g2 == proposed_gate and gate_of_f1 == g1
                if condition1 == True or condition2 == True:
                    return False

    return True

def reassign_vertices(solution, weights, M_validGate, P_preferences):
    """
    Reassign all non-mandatory dummy gate assignments.
    """
    for i in range(len(weights)):
        if solution[i] == 'Dum' and M_validGate[i]:
            best_gate = max((P_preferences[i][g], g) for g in M_validGate[i] if g != 'Dum')[1]
            solution[i] = best_gate

def eliminate_conflicts(solution, M_validGate, U_successor):
    """
    Removes gate conflicts by reassigning conflicting flights to alternative gates or to a dummy gate if no alternatives exist.
    """
    for i in range(len(solution)):
        for j in range(i + 1, len(solution)):
            if solution[i] == solution[j] and solution[i] != 'Dum':  # Check only non-dummy assignments
                if not (U_successor.get(i) == j or U_successor.get(j) == i):
                    reassigned = False
                    # Attempt to reassign j to another valid gate
                    for gate in M_validGate[j]:
                        if gate not in solution and gate != 'Dum':
                            solution[j] = gate
                            reassigned = True
                            break
                    if not reassigned:
                        solution[j] = 'Dum'  # Fallback to dummy gate if no valid reassignment found

def initialize_clusters2(initial_solution, num_activities, num_gates, weights):
    """
    (Algorithm 2)
    Generates an initial solution for gate assignments by iteratively assigning activities to gates
    that provide the best heuristic improvement. This greedy approach helps establish a starting point
    for further optimization processes.

    Parameters:
        initial_solution (list): List pre-filled with 'Dum' or another placeholder to denote unassigned gates.
        num_activities (int): Total number of activities to be assigned gates.
        num_gates (int): Total number of available gates.
        weights (list of lists): Matrix representing the interaction costs or benefits between activities and gates.

    Returns:
        list: An initial gate assignment solution, where each activity is assigned to an optimal starting gate.

    """
    solution = initial_solution[:]
    non_tabu = set(range(num_activities))

    while non_tabu:
        for i in list(non_tabu):
            best_improvement = -np.inf
            best_gate = None

            for g in range(num_gates):
                if g != solution[i]:
                    improvement = calculate_heuristic_value(i, solution, g, weights)
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_gate = g

            if best_gate is not None:
                solution[i] = best_gate
                non_tabu.remove(i)
        else:
            # Move to a dummy gate if no improvement found, or manage conflicts
            solution[i] = 'Dum'

    return solution

def initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor):
    """
    (Algorithm 2)
    Generates an initial solution for gate assignments by iteratively assigning activities to gates
    that provide the best heuristic improvement. This greedy approach helps establish a starting point
    for further optimization processes.

    Parameters:
        weights (list of lists): Matrix representing the interaction costs or benefits between activities and gates.
        others: required for functions used inside.

    Returns:
        list: An initial gate assignment solution, where each activity is assigned to an optimal starting gate.

    """
    activities = list(activities_to_flights.keys())     # ['arr_1', 'dep_1', ...]
    gates = list(gates_to_indices.keys())               # ['120', '122', ...]
    C_list = activities + gates                         # ['arr_1', 'dep_1', ..., '120', '122', ...] (initial cluster)
    C_dict = {}     # current Cluster
    # for i in range(len(Vertices)):
    #     C_dict[f'C{i+1}'] = [C_list[i]]   # { 'C1': ['arr_1'], 'C2': ['dep_1'], ... }

    D_clusters = {f'D{i+1}': [gates[i]] for i in range(len(gates))}        # { 'D1': ['120'], 'D2': ['122'], ... }
    D_clusters['Dummy'] = ['Dum']

    '''
    for non_tabu_Activities, paper says U(i) != 0 and U(U(i)) != 0 means arrival, but we have some arrivals for whom their departure has no successor
    -> commented lines should be used for the paper, but uncommented lines are used for our specific instance
    '''
    # non_tabu_Activities = [i for i in C_list if (U_successor[i] !=0 and U_successor[U_successor[i]] != 0)]
    non_tabu_Activities = [activity for activity in C_list if activity[0:3] == 'arr']
    non_tabu = len(non_tabu_Activities)

    while non_tabu > 0:
        i = non_tabu_Activities[0]      # Check first non_tabu activity
        best_improvement = -np.inf

        for D in D_clusters.keys():
            D_key = D
            D_list = D_clusters[D_key]      # = ['gate'] or D = ['gate', i, Ui, UUi], or D = ['gate', i1, Ui1, UUi1, i2, Ui2, UUi2, ...] or ...
            Ui = U_successor[i]
            # UUi = U_successor[U_successor[i]]

            h1 = calculate_heuristic_value(i, C_list, D_list, weights, activities_to_flights, gates_to_indices)
            h2 = calculate_heuristic_value(Ui, C_list, D_list, weights, activities_to_flights, gates_to_indices)
            # h3 = calculate_heuristic_value(UUi, C_list, D_list, weights, activities_to_flights, gates_to_indices)
            # improvement = h1 + h2 + h3
            improvement = h1 + h2
            if improvement > best_improvement:
                best_improvement = improvement
                D_star_value = D_list
                D_star_key = D_key

        if best_improvement > 0:
            # D_star_value.extend([i, Ui, UUi])
            D_star_value.extend([i, Ui])
            D_clusters[D_star_key] = D_star_value

        del non_tabu_Activities[0]
        non_tabu -= 1

    return D_clusters

def refine_clusters(current_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                         activities_to_flights, gates_to_indices):
    """
    (Algorithm 1)
    Refines initial gate assignments for flights using a tabu search heuristic. The function iteratively
    explores the assignment of flights to different gates, trying to find a configuration that improves
    the objective function defined by the given weights matrix.

    Algorithm 1 should return the best solution found along your solution chain, not the last solution found!
    The idea of the ejection chain is to "eject" the solution from your chain which has the best objective. This
    is not necessarily the very last solution found.

    Parameters:
        initial_clusters (list): Initial gate assignments for each flight.
        num_flights (int): Total number of flights that need gate assignments.
        num_gates (int): Total number of available gates.
        weights (list of lists): A matrix representing the weights (or cost) between different vertices (flights).

    Returns:
        list: Refined gate assignments after applying the heuristic optimization.
    """

    # no_nodes = len(weights)

    # Initialization
    duplicate_solution = current_solution
    nontabu_vertices = current_solution
    best_score = calculate_total_score(current_solution, weights)
    tabu_activities = set()
    tabu_vertices = set()
    moves_made = 0
    current_score = calculate_total_score(current_solution, weights)
    best_score = 0
    can_improve_more = True

    while can_improve_more:
        for vertex in duplicate_solution.keys():
            best_move = None
            best_improvement = -np.inf
            for activity in duplicate_solution[vertex][1:]: # dup... = { 'D1': ['gate', 'activity1', 'activity2', ...], 'D2': [...], ... }
                if activity in tabu_activities:
                    continue    # If activity has already been checked, continue to next activity
                elif (vertex not in tabu_vertices) and len(nontabu_vertices) > 0:
                    # allOtherVertices = current_solution
                    # del allOtherVertices[vertex]
                    for C in nontabu_vertices.keys():     # = for all clusters left (not yet tabu) = for all gates (1 gate per cluster)
                        proposed_gate = nontabu_vertices[C][0]
                        move_allowed = is_move_feasible(activity, proposed_gate, nontabu_vertices, shadow_constraints, flights_to_activities,
                         activities_to_flights)
                        if move_allowed == True:
                            print('--- A move was allowed')
                            proposed_Cluster = C
                            current_solution_list = [vertices[i] for vertices in current_solution.values() for i in range(len(vertices))]
                            D_Cluster_list = nontabu_vertices[C][1:]    # Exclude gate
                            potential_improvement = calculate_heuristic_value(activity, current_solution_list, D_Cluster_list, weights, activities_to_flights, gates_to_indices)
                            if potential_improvement > best_improvement:
                                best_improvement = potential_improvement
                                best_move = (activity, proposed_Cluster)

                if best_move:
                    moves_made += 1
                    # Make tabu changes
                    tabu_activities.add(activity)
                    tabu_vertices.add(proposed_Cluster)
                    # Make cluster changes
                    del nontabu_vertices[proposed_Cluster]
                    duplicate_solution[vertex].remove(activity)     # Remove activity from its previous cluster ...
                    duplicate_solution[proposed_Cluster].append(activity)   # ... and add it to the cluster it moves to

                    # Find max objective of duplicate after r moves
                    duplicate_objective = calculate_total_score(duplicate_solution, weights)
                    if duplicate_objective > best_score and duplicate_objective > best_scorecurrent_score:
                        best_score = duplicate_objective
                        r = moves_made
                        best_solution = duplicate_solution
        if r > 0:
            duplicate_solution = best_solution
        else:
            can_improve_more = False

        # for i in range(num_activities):
        #     if i in tabu_list:
        #         continue  # Skip processing for tabu flights
        #
        #     current_cluster = current_solution[i]
        #     # Iterate through all potential new clusters for vertex i
        #     for D in range(num_gates):
        #         if D != current_cluster and (i, D) not in tabu_list:
        #             if is_move_feasible(i, D, current_solution, shadow_constraints, flights_to_activities,
        #                  activities_to_flights):
        #
        #                 # potential_improvement = calculate_heuristic_value(no_nodes, weights)
        #                 potential_improvement = calculate_heuristic_value(i, current_cluster, D, weights)
        #
        #
        #                 if potential_improvement > best_improvement:
        #                     best_improvement = potential_improvement
        #                     best_move = (i, D)
        # if best_move:
        #     i, D = best_move
        #     current_solution[i] = D
        #     tabu_list.add((i, D))  # Add move to tabu list
        #     changed = True
        #     current_score = calculate_total_score(current_solution, weights)
        #     # print(f"Moving Vertex {i} to Cluster {D}, marking Vertex {i} as tabu.")
        #
        #     if current_score > best_score:
        #         best_score = current_score
        #         best_solution = current_solution[:]

    return best_solution


def apply_two_opt_step(solution, weights, C):
    """
    Applies a 2-opt algorithm to refine gate assignments by non-sequentially swapping pairs of activities
    and checking if the swaps result in a reduced total cost or improved solution. The function iterates
    over all pairs of activities that meet a certain condition based on C, and performs swaps if they improve
    the total score of the solution.

    Parameters:
        solution (list): The current list of gate assignments for each activity.
        weights (list of lists): Matrix representing the cost or conflicts between each pair of activities.
        C (list): A list of categories or conditions that restrict which activities can be swapped.

    Returns:
        list: The optimized solution after applying the 2-opt swaps.
    """

    improved = True
    while improved:
        improved = False
        for i in range(len(solution)):
            for j in range(i + 1, len(solution)):
                if C[solution[i]] != C[solution[j]]:
                    # Perform the swap
                    solution[i], solution[j] = solution[j], solution[i]
                    current_score = calculate_total_score(solution, weights)
                    # Swap back to undo
                    solution[i], solution[j] = solution[j], solution[i]
                    new_score = calculate_total_score(solution, weights)

                    # If the new configuration is better, accept the swap permanently
                    if new_score < current_score:
                        solution[i], solution[j] = solution[j], solution[i]
                        improved = True
    return solution


def iterative_refinement_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                           shadow_constraints, num_flights,
                                           activities_to_flights, gates_to_indices, flights_to_activities):
    """
    (Algorithm 3)
    Optimizes flight gate assignments by iteratively refining an initial solution through a heuristic approach.
    The process starts by assigning all activities to a 'dummy' gate, followed by refining these assignments
    to reduce conflicts and improve the overall solution quality.

    The function repeatedly refines the gate assignments, assessing improvements and updating the solution
    until no further improvements can be achieved or a maximum of seven iterations is reached. Each iteration
    checks if the newly refined solution offers a better score than the previous best; if not, it may terminate
    early or continue to explore other potential improvements.

    Returns:
        list: Best found solution.
    """
    current_solution = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_solution = refine_clusters(current_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                    activities_to_flights, gates_to_indices)
    best_score = calculate_total_score(best_solution, weights)
    # print("Initial best solution and score from refinement:", best_solution, best_score)

    run_count = 0
    while run_count < 7:
        refined_solution = refine_clusters(current_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score = calculate_total_score(refined_solution, weights)

        if current_score == best_score:
            print("No improvement in solution; terminating the process.")
            break  # Terminate the process if no improvement is found

        elif current_score > best_score:
            best_solution = refined_solution[:]
            best_score = current_score
            run_count = 0  # Reset the run count if improvement is found
            print("New best solution found, score updated:", best_score)

        else:
            run_count += 1  # Increment run count if no improvement

        # Reassign any non-optimal gate assignments
        reassign_vertices(refined_solution, weights, M_validGate, P_preferences)
        # Handle any conflicts in the solution
        eliminate_conflicts(refined_solution, M_validGate, U_successor)

    return best_solution


def pre_optimized_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                         activities_to_flights, gates_to_indices, flights_to_activities):
    """
    Optimizes gate assignments by integrating a 2-opt optimization step immediately after initial clustering.
    This method begins by assigning all activities to a 'dummy' gate, then applies a 2-opt algorithm to improve the initial
    clustering. Following this, it employs a tabu search-like iterative refinement to further optimize the gate assignments.

    The process aims to improve the starting configuration, potentially leading to better final solutions. It iterates through
    refinement and reassessment up to seven times or until no further improvements are found. Activities are reassigned
    from 'dummy' gates when necessary, and conflicts are managed to ensure all operational constraints are met.

    Returns:
        list: The best gate assignment solution found.
    """
    current_solution = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_solution = refine_clusters(current_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
    best_score = calculate_total_score(best_solution, weights)

    run_count = 0
    while run_count < 7:
        # Apply a 2-opt step to refine the solution further by examining pairs of activities
        two_opt_refined_solution = apply_two_opt_step(current_solution, weights, U_successor)
        refined_solution = refine_clusters(two_opt_refined_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score = calculate_total_score(refined_solution, weights)

        if current_score > best_score:
            best_solution = refined_solution[:]
            best_score = current_score
            run_count = 0  # Reset if an improvement is found
        else:
            run_count += 1  # Continue if no improvement

        # Reassign any non-optimal gate assignments and handle conflicts
        reassign_vertices(refined_solution, weights, M_validGate, P_preferences)
        eliminate_conflicts(refined_solution, M_validGate, U_successor)

    return best_solution


def integrated_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                      activities_to_flights, gates_to_indices, flights_to_activities):
    """
    Optimizes gate assignments by integrating a 2-opt strategy with heuristic refinement.
    Begins with an initial setup where all activities are assigned to a 'dummy' gate, followed by a 2-opt optimization
    to improve the starting configuration. The process continues with iterative refinement, adjusting gate assignments
    to minimize conflicts based on a weight matrix, until no further improvements are found or a limit of seven
    iterations is reached.

    Returns:
        list: Best found solution.
    """
    current_solution = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_solution = apply_two_opt_step(current_solution, weights, U_successor)  # Apply 2-opt optimization here
    best_score = calculate_total_score(best_solution, weights)

    # Further refinement loop
    run_count = 0
    while run_count < 7:
        refined_solution = refine_clusters(best_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score = calculate_total_score(refined_solution, weights)

        if current_score < best_score:
            best_solution = refined_solution[:]
            best_score = current_score
            run_count = 0  # Reset the run count if improvement is found
        else:
            run_count += 1  # Increment run count if no improvement

        # Reassign any non-optimal gate assignments and handle conflicts
        reassign_vertices(refined_solution, weights, M_validGate, P_preferences)
        eliminate_conflicts(refined_solution, M_validGate, U_successor)

    return best_solution