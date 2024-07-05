import numpy as np


def calculate_heuristic_value(i, C, D, weights):
    """
    Calculate the heuristic value for moving vertex i from its current cluster C[i] to a new cluster D.
    """
    # print("-----------------ABC------------------")
    # print(weights, "---------", len(weights))
    # print("JE SUIS ICI")
    # print(C, "---------", len(C))
    # print("-----------------DEF------------------")
    sum_weights_new_cluster = sum(weights[i][j] for j in range(len(weights)) if C[j] == D)
    sum_weights_current_cluster = sum(weights[i][j] for j in range(len(weights)) if C[j] == C[i] and j != i)
    return sum_weights_new_cluster - sum_weights_current_cluster


def calculate_total_score(solution, weights):
    """
    Calculate the total score of the current solution based on the weights matrix.
    """
    score = 0
    for i in range(len(weights)):
        for j in range(i + 1, len(weights)):
            if solution[i] == solution[j] and solution[i] != 'Dum':
                score += weights[i][j]
                # Do I need to consider succeor here?
    return score


def is_move_feasible(i, proposed_gate, current_solution, shadow_constraints):
    """
    Checks if moving flight `i` to `proposed_gate` violates any shadow constraints.
    """
    for (f1, g1, f2, g2) in shadow_constraints:
        if (f1 == i and g1 == proposed_gate and current_solution[f2] == g2) or \
                (f2 == i and g2 == proposed_gate and current_solution[f1] == g1):
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


'''
def initialize_clusters(initial_solution, num_flights, num_gates, weights):
    """
    (Algorithm 2)
    Generates an initial solution for gate assignments.

    Returns:
        list: Updated gate assignments with optimized initial clustering.
    """

    no_nodes = len(weights)

    initial_clusters = initial_solution[:] # every flight to dummy gate
    # print("alg2_initial:", alg2_initial)
    non_tabu = set(range(num_flights)) # Set all vertices as non-tabu initially

    # Iterate until there are non-tabu vertices to process
    while non_tabu:
        best_improvement = float('-inf')
        best_vertex, best_cluster = None, None

        # Iterate over all non-tabu vertices
        for vertex in non_tabu:
            current_cluster = initial_clusters[vertex]

            # Evaluate all possible clusters D for this vertex
            for new_cluster in range(num_gates):
                if new_cluster == current_cluster:
                    continue

                # Calculate the potential heuristic improvement
                improvement = calculate_heuristic_value(no_nodes, weights)
                # print(f"Evaluating move of Vertex {i} to Cluster {D}: Improvement {improvement}")
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_vertex, best_cluster = vertex, new_cluster
                    # print(f"New best move found: Move Vertex {i} to Cluster {D} with improvement {improvement}")

        if best_vertex is not None:
            # Assign the best vertex to the best cluster and mark it as tabu
            initial_clusters[best_vertex] = best_cluster
            non_tabu.remove(best_vertex)
            # print(f"Moving Vertex {best_i} to Cluster {best_D} , marking Vertex {best_i} as tabu.")

        else:
            print("No improving move found, exiting loop.")
            break  # Exit if no improving move is found

    # Assign all flights without a gate to the dummy gate
    for vertex in range(num_flights):
        if initial_clusters[vertex] is None:
            initial_clusters[vertex] = no_nodes

    return initial_clusters
'''


def initialize_clusters(initial_solution, num_activities, num_gates, weights):
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


def refine_clusters(initial_clusters, num_flights, num_gates, weights, shadow_constraints):
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

    no_nodes = len(weights)

    # Initialization
    current_solution = initial_clusters[:]
    best_solution = current_solution[:]
    best_score = calculate_total_score(current_solution, weights)
    tabu_list = set()
    iteration = 0
    changed = True

    while changed:
        changed = False
        best_move = None
        best_improvement = -np.inf

        for i in range(num_flights):
            if i in tabu_list:
                continue  # Skip processing for tabu flights

            current_cluster = current_solution[i]
            # Iterate through all potential new clusters for vertex i
            for D in range(num_gates):
                if D != current_cluster and (i, D) not in tabu_list:
                    if is_move_feasible(i, D, current_solution, shadow_constraints):

                        potential_improvement = calculate_heuristic_value(no_nodes, weights)
                        # print(f"Evaluating move of Vertex {i} from Cluster {current_cluster} to Cluster {D}: Improvement {current_improvement}")

                        if potential_improvement > best_improvement:
                            best_improvement = potential_improvement
                            best_move = (i, D)
        if best_move:
            i, D = best_move
            current_solution[i] = D
            tabu_list.add((i, D))  # Add move to tabu list
            changed = True
            current_score = calculate_total_score(current_solution, weights)
            # print(f"Moving Vertex {i} to Cluster {D}, marking Vertex {i} as tabu.")

            if current_score > best_score:
                best_score = current_score
                best_solution = current_solution[:]

        iteration += 1
        # print(f"Iteration {iteration} of algorithm 1 completed with solution: {solution}")
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


def iterative_refinement_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences):
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
    initial_solution = ['Dum'] * num_activities
    current_solution = initialize_clusters(initial_solution, num_activities, num_gates, weights)
    best_solution = refine_clusters(current_solution, num_activities, weights)
    best_score = calculate_total_score(best_solution, weights)
    print("Initial best solution and score from refinement:", best_solution, best_score)

    run_count = 0
    while run_count < 7:
        refined_solution = refine_clusters(current_solution, num_activities, weights)
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


def pre_optimized_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences):
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
    initial_solution = ['Dum'] * num_activities
    current_solution = initialize_clusters(initial_solution, num_activities, num_gates, weights)
    best_solution = refine_clusters(current_solution, num_activities, weights)
    best_score = calculate_total_score(best_solution, weights)

    run_count = 0
    while run_count < 7:
        # Apply a 2-opt step to refine the solution further by examining pairs of activities
        two_opt_refined_solution = apply_two_opt_step(current_solution, weights, U_successor)
        refined_solution = refine_clusters(two_opt_refined_solution, num_activities, weights)
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


def integrated_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences):
    """
    Optimizes gate assignments by integrating a 2-opt strategy with heuristic refinement.
    Begins with an initial setup where all activities are assigned to a 'dummy' gate, followed by a 2-opt optimization
    to improve the starting configuration. The process continues with iterative refinement, adjusting gate assignments
    to minimize conflicts based on a weight matrix, until no further improvements are found or a limit of seven
    iterations is reached.

    Returns:
        list: Best found solution.
    """
    initial_solution = ['Dum'] * num_activities
    current_solution = initialize_clusters(initial_solution, num_activities, num_gates, weights)
    best_solution = apply_two_opt_step(current_solution, weights, U_successor)  # Apply 2-opt optimization here
    best_score = calculate_total_score(best_solution, weights)

    # Further refinement loop
    run_count = 0
    while run_count < 7:
        refined_solution = refine_clusters(best_solution, num_activities, weights)
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