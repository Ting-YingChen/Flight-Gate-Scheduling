


def calculate_heuristic_value(vertices, weights):
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
    '''Feedback 12.06.:
    ALWAYS pass all parameters relevant for a function (i, C, D) as an argument!
    '''

    # Current cluster of vertex i
    C_i = C[i]

    # Sum of weights of edges between vertex i and all vertices in the new cluster D
    sum_weights_new_cluster = sum(weights[i][j] for j in range(vertices) if C[j] == D)

    # Sum of weights of edges between vertex i and all vertices in its current cluster C(i), excluding i itself
    sum_weights_current_cluster = sum(weights[i][j] for j in range(vertices) if C[j] == C_i and j != i)

    # Heuristic value h(i, C(i), D)
    h_value = sum_weights_new_cluster - sum_weights_current_cluster

    return h_value


# Example usage of heuristic function
vertices, weights = get_weight_matrix(num_flights, num_gates, T, P, U, M, alpha1, alpha2, alpha3, t_max)

# Current cluster assignments for all vertices
'''Feedback 12.06.:
why do you get cluster assignments from the MIP? You should start with initial clusters according to Algorithm 2.
'''
_, _, C = build_cpp_model(vertices, weights)
print("Current cluster C: ", C)

# Loop to calculate heuristic values for every vertex i and every possible neighbor D
for i in range(num_flights):
    '''Feedback 12.06.:
    why only iterate until num_gates-1? AFAIK there are "no. of gates" many clusters.
    '''

    for D in range(num_gates - 1):
        if D != C[i]:  # Ensure that we do not consider moving a vertex to its current cluster
            h_value = calculate_heuristic_value(vertices, weights)
            print(
                f"Heuristic value for moving vertex {i} (Flight {i + 1}) to vertex {num_flights + D} (Gate {D + 1}): {h_value}")


##############################################################################################

'''Feedback 12.06.:
Function names should always precisely describe what the function is supposed to do. The same holds for inputs
(and variable names in general).
'''


def algorithm_2(alg2_initial):
    """
    Generate an initial solution, trying to avoid assigning flights to the dummy gate unless necessary.

    """

    # Initial solution setup: No two vertices are related
    solution = alg2_initial[:]
    # print("alg2_initial:", alg2_initial)

    # Set all vertices as non-tabu initially
    non_tabu = set(range(num_flights))

    # Iterate until there are non-tabu vertices to process
    while non_tabu:
        best_improvement = float('-inf')
        best_i, best_D = None, None

        # Iterate over all non-tabu vertices
        for i in non_tabu:
            '''Feedback 12.06.: why skip a vertex if its successor is tabu?
            '''
            if U[i] != 0 and U[i] not in non_tabu:
                continue  # Skip if the vertex is a successor and the successor is tabu
            current_cluster = solution[i]
            # print('\n', f"Checking moves form Vertex {i} from Cluster {current_cluster}")

            # Evaluate all possible clusters D for this vertex
            for D in range(num_gates):
                if D == current_cluster:
                    continue

                # Calculate the potential heuristic improvement
                improvement = calculate_heuristic_value(vertices, weights)
                # print(f"Evaluating move of Vertex {i} to Cluster {D}: Improvement {improvement}")

                if improvement > best_improvement:
                    best_improvement = improvement
                    best_i, best_D = i, D
                    # print(f"New best move found: Move Vertex {i} to Cluster {D} with improvement {improvement}")

        if best_i is not None:
            # Assign the best vertex to the best cluster and mark it as tabu
            solution[best_i] = best_D
            non_tabu.remove(best_i)
            # print(f"Moving Vertex {best_i} to Cluster {best_D} , marking Vertex {best_i} as tabu.")

        else:
            print("No improving move found, exiting loop.")
            break  # Exit if no improving move is found

    # Assign all flights without a gate to the dummy gate
    for i in range(num_flights):
        if solution[i] is None:
            solution[i] = vertices

    return solution

# Example usage:
# alg2_initial = [None]* vertices
# alg2_initial = C

# Run algorithm 2
# alg2_solution = algorithm_2(alg2_initial)
# print("alg2_solution:", alg2_solution)

##################################################################################
def algorithm_3(vertices, weights, U, M, P):
    """
    Executes Algorithm 3 to iteratively refine the solution by running Algorithms 2 and 1.

    Parameters:
        vertices (int): Total number of vertices (flights + gates).
        weights (list of lists): Weight matrix representing interaction between vertices.
        U (list): List containing successor information for each flight.
        M (list): Valid gate assignments for each flight.
        P (list of lists): Preferences matrix for flights against gates.
        initial_solution (list): Starting solution template, typically with no assignments.

    Returns:
        list: Best found solution.
    """

    # Initial solution from Algorithm 2
    '''Feedback 12.06.:
    Initialization should not be done using the MIP (this is kinda like cheating), but instead using algorithm_1.
    '''
    current_solution = algorithm_2(alg2_initial=C)
    print("Initial solution from CPP MIP:", C)
    print("Initial solution from Algorithm 2:", current_solution)

    # Refinement from Algorithm 1
    best_solution = algorithm_1(alg1_initial=current_solution)
    best_score = calculate_total_score(best_solution, weights, vertices)
    print("Initial best solution and score from Algorithm 1:", best_solution, best_score)

    run_count = 0
    while run_count < 7:
        current_solution = algorithm_2(alg2_initial=C)
        '''Feedback 12.06.: don't call algorithm_2 here! Algorithm_2 only gives you an initial solution at the very beginning
        of the heuristic and is never called again thereafter
        '''
        refined_solution = algorithm_1(current_solution)
        current_score = calculate_total_score(refined_solution, weights, vertices)
        print(f"Run {run_count}: Refined solution and score:", refined_solution, current_score)

        '''Feedback 12.06.: logic here needs to be changed:
        If current_score == best_score -> terminate: ejection chain
        could not improve the solution
        Else: continue on with reassignments
        '''
        if current_score > best_score:
            best_solution = refined_solution[:]
            best_score = current_score
            run_count = 0  # Reset if improvement is found
            print("New best solution found, score updated.")
        else:
            run_count += 1  # Increment if no improvement

        # Reassign all non-mandatory dummy gate assignments
        '''Feedback 12.06.: put this into a function reassign_vertices()'''
        for i in range(vertices):
            if U[i] == 0 or U[U[i]] == i:
                continue
            if refined_solution[i] == vertices:  # Dummy gate index
                # Assign to the best available gate
                best_gate = max((P[i][k], k) for k in M[i])[1]
                refined_solution[i] = best_gate
                print(f"Vertex {i} reassigned from dummy to Gate {best_gate}")

        # Eliminate gate and shadow conflicts
        eliminate_conflicts(refined_solution, M, U)
        print("Conflicts eliminated, current intermediate solution:", refined_solution)

    return best_solution


def eliminate_conflicts(solution, M, U):
    """
    Removes any gate and shadow conflicts from the solution.

    Parameters:
        solution (list): The current solution array representing gate assignments.
        M (list): Valid gate assignments for each flight.
        U (list): Successor information.
    """
    for i in range(len(solution)):
        for j in range(len(solution)):
            if i != j and solution[i] == solution[j]:
                if not any(U[k] == i for k in range(len(U))):
                    # If not a successor, resolve conflict
                    solution[j] = None  # Or assign to a different gate


def calculate_total_score(solution, weights, vertices):
    """
    Calculate the total score of the current solution based on the weights matrix.

    Parameters:
        solution (list): The list of gate assignments for each vertex.
        weights (list of lists): The weights matrix.
        vertices (int): Total number of vertices.

    Returns:
        int: The calculated score.
    """
    score = 0
    for i in range(vertices):
        for j in range(i + 1, vertices):
            if solution[i] == solution[j]:
                score += weights[i][j]
    return score


alg3_solution = algorithm_3(vertices, weights, U, M, P)
print("alg3_solution", alg3_solution)