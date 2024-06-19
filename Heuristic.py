from Example_Input import num_flights, num_gates, T, P, U, M, alpha1, alpha2, alpha3, t_max, shadow_constraints

def calculate_heuristic_value(i, C, D, vertices, weights):
    """
    Calculate the heuristic value for moving vertex i from its current cluster C(i) to a new cluster D.

    Parameters:
        i (int): The vertex to be moved.
        C (list): The current clusters of all vertices.
        D (int): The new cluster to which vertex i will be moved.
        weights (list of lists): The adjacency matrix representing the weights between vertices.
        vertices (int): Total number of vertices.

    Returns:
        float: The heuristic value of the move.
    """

    # Current cluster of vertex i
    C_i = C[i]

    # Sum of weights of edges between vertex i and all vertices in the new cluster D
    sum_weights_new_cluster = sum(weights[i][j] for j in range(vertices) if C[j] == D)

    # Sum of weights of edges between vertex i and all vertices in its current cluster C(i), excluding i itself
    sum_weights_current_cluster = sum(weights[i][j] for j in range(vertices) if C[j] == C_i and j != i)

    # Heuristic value h(i, C(i), D)
    h_value = sum_weights_new_cluster - sum_weights_current_cluster

    return h_value

def is_move_feasible(i, proposed_gate, current_solution, shadow_constraints):
    """
    Checks if moving flight `i` to `proposed_gate` violates any shadow constraints.
    """
    for (f1, g1, f2, g2) in shadow_constraints:
        if (f1 == i and g1 == proposed_gate and current_solution[f2] == g2) or \
           (f2 == i and g2 == proposed_gate and current_solution[f1] == g1):
            return False  # Move is not feasible due to shadow constraint
    return True

def calculate_total_score(solution, vertices, weights):
    """
    Calculate the total score of the current solution based on the weights matrix, where higher weights
    indicate a penalty for assigning two vertices to the same gate.

    Parameters:
        solution (list): The list of gate assignments for each vertex.
        weights (list of lists): The weights matrix, penalizing undesirable pairings.
        vertices (int): Total number of vertices.

    Returns:
        int: The calculated score, where lower scores are better.
    """
    score = 0
    for i in range(vertices):
        if solution[i] is None:  # Skip if no gate assigned
            continue
        for j in range(i + 1, vertices):
            if solution[i] is not None and solution[i] == solution[j]:
                score += weights[i][j]  # Only add weight if both vertices are assigned the same gate

    return score

def reassign_vertices(solution, vertices, M, P, U):
    """
    Reassign all non-mandatory dummy gate assignments.

    Parameters:
        solution (list): The current solution array representing gate assignments.
        vertices (int): Number of vertices.
        M (list): Valid gate assignments for each flight.
        P (list of lists): Preferences matrix for flights against gates.
        U (list): Successor information.
    """
    for i in range(vertices):
        if solution[i] == vertices:  # Check if assigned to the dummy gate (dummy gate index = vertices)
            # Find the best available gate according to preferences
            if M[i]:  # Ensure there are valid gates available for reassignment
                best_gate = max((P[i][k], k) for k in M[i])[1]
                solution[i] = best_gate
                print(f"Vertex {i} reassigned from dummy to Gate {best_gate}")

def eliminate_conflicts(solution, M, U):
    """
    Removes any gate and shadow conflicts from the solution by ensuring that no two flights without a successor
    relationship are assigned to the same gate.

    Parameters:
        solution (list): The current solution array representing gate assignments.
        M (list): Valid gate assignments for each flight.
        U (list): Successor information, where U[i] is the successor of flight i if one exists.
    """

    for i in range(len(solution)):
        for j in range(len(solution)):
            if i != j and solution[i] == solution[j]:
                if not any(U[k] == i for k in range(len(U))):
                    # If not a successor, resolve conflict
                    solution[j] = None  # Or assign to a different gate

def initialize_clusters(initial_solution, num_flights, num_gates, vertices, weights):
    """
    (Algorithm 2)
    Generates an initial solution for flight gate assignments, trying to avoid assigning flights to the dummy gate
    unless necessary.

    Parameters:
        initial_solution (list): Current gate assignments, possibly incomplete.
        num_flights (int): Total number of flights.
        num_gates (int): Total number of actual gates (excluding dummy).
        vertices (int): Total number of vertices; used here to denote a dummy gate.
        weights (list of lists): Adjacency matrix representing the weights between vertices, used for heuristic calculations.

    Returns:
        list: Updated gate assignments with optimized initial clustering.
    """

    initial_clusters = initial_solution[:]
    # print("alg2_initial:", alg2_initial)
    non_tabu = set(range(num_flights)) # Set all vertices as non-tabu initially

    # Iterate until there are non-tabu vertices to process
    while non_tabu:
        best_improvement = float('-inf')
        best_vertex, best_cluster = None, None

        # Iterate over all non-tabu vertices
        for vertex in non_tabu:
            current_cluster = initial_clusters[vertex]
            '''Feedback 12.06.: why skip a vertex if its successor is tabu?
            '''
            if U[vertex] != 0 and U[vertex] not in non_tabu:
                continue  # Skip if the vertex is a successor and the successor is tabu

            # Evaluate all possible clusters D for this vertex
            for new_cluster in range(num_gates):
                if new_cluster == current_cluster:
                    continue

                # Calculate the potential heuristic improvement
                improvement = calculate_heuristic_value(vertices, weights)
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
            initial_clusters[vertex] = vertices

    return initial_clusters

def refine_clusters(initial_clusters, num_flights, num_gates, vertices, weights):

    """
    (Algorithm 1)
    Refines initial gate assignments for flights using a tabu search heuristic. The function iteratively
    explores the assignment of flights to different gates, trying to find a configuration that improves
    the objective function defined by the given weights matrix.

    Parameters:
        initial_clusters (list): Initial gate assignments for each flight.
        num_flights (int): Total number of flights that need gate assignments.
        num_gates (int): Total number of available gates.
        vertices (int): Total number of vertices in the model, used for constraints.
        weights (list of lists): A matrix representing the weights (or cost) between different vertices (flights).

    Returns:
        list: Refined gate assignments after applying the heuristic optimization.
    """

    # Ensure every vertex has a default initial cluster if not assigned
    current_solution = initial_clusters[:]
    best_solution = current_solution[:]
    best_score = float('-inf')
    tabu_list = set()
    iteration = 0
    changed = True


    while changed:
        changed = False
        best_move = None
        best_improvement = float('-inf')

        for i in range(num_flights):
            if i in tabu_list:
                continue # Skip processing for tabu flights

            current_cluster = current_solution[i]
            # Iterate through all potential new clusters for vertex i
            for D in range(num_gates):
                if D != current_cluster and D not in tabu_list and \
                        is_move_feasible(i, D, current_solution, shadow_constraints):

                    potential_improvement = calculate_heuristic_value(vertices, weights)
                    #print(f"Evaluating move of Vertex {i} from Cluster {current_cluster} to Cluster {D}: Improvement {current_improvement}")
                    if potential_improvement > best_improvement:
                        best_improvement = potential_improvement
                        best_move = (i, D)

        if best_move:
            i, D = best_move
            current_solution[i] = D
            tabu_list.add(i)
            changed = True
            current_score = calculate_total_score(current_solution, vertices, weights)
            #print(f"Moving Vertex {i} to Cluster {D}, marking Vertex {i} as tabu.")

            if current_score > best_score:
                best_score = current_score
                best_solution = current_solution[:]

        iteration += 1
        #print(f"Iteration {iteration} of algorithm 1 completed with solution: {solution}")

    '''Algorithm 1 should return the best solution found along your solution chain, not the last solution found!
    The idea of the ejection chain is to "eject" the solution from your chain which has the best objective. This
    is not necessarily the very last solution found.   
    '''
    return best_solution

def iterative_gate_optimization(vertices, weights, U, M, P):
    """
    Optimizes flight gate assignments by iteratively refining solutions through heuristic approaches.
    Initializes the solution with an algorithm, then refines it, and checks for improvements,
    repeating the refinement until no further improvements can be made or a set number of iterations is reached.

    Parameters:
        vertices (int): Total number of vertices (flights + gates).
        weights (list of lists): Weight matrix representing interaction between vertices.
        U (list): List containing successor information for each flight.
        M (list): Valid gate assignments for each flight.
        P (list of lists): Preferences matrix for flights against gates.

    Returns:
        list: Best found solution.
    """
    current_solution = initialize_clusters(vertices, weights, U, M, P)
    best_solution = refine_clusters(current_solution, vertices, weights)
    best_score = calculate_total_score(best_solution, weights, vertices)
    print("Initial best solution and score from refinement:", best_solution, best_score)

    run_count = 0
    while run_count < 7:
        refined_solution = refine_clusters(current_solution, vertices, weights)
        current_score = calculate_total_score(refined_solution, weights, vertices)

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
        reassign_vertices(refined_solution, vertices, M, P, U)
        # Handle any conflicts in the solution
        eliminate_conflicts(refined_solution, M, U)

    return best_solution