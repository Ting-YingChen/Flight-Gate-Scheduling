import numpy as np
import time
import copy
import random

def calculate_heuristic_value(i, C, D, weights, activities_to_flights, gates_to_indices):
    """ Calculate the heuristic value for moving vertex i from its current cluster C[i] to a new cluster D """
    # C = current cluster (list of all vertices of that cluster)
    # D = new (possibly empty) cluster (list of the vertices of that cluster)

    sum_weights_new_cluster = sum(weights[i][j] for j in D if j != 'Dum')
    sum_weights_current_cluster = sum(weights[i][j] for j in C if (j != i and j != 'Dum'))
    return sum_weights_new_cluster - sum_weights_current_cluster

def calculate_total_score(solution, weights, large_negative):
    """ Calculate the total score of the current solution based on the weights matrix.
    Paper p.294, ultimate paragraph: "The CPP is to find an equivalence relation on V so that the sum of the edge
    weights of all vertices IN RELATION is maximized. This is equivalent to finding a partition of V into cliques,
    i.e., a vertex subset, so that the sum of the edge weights WITHIN the cliques is maximized. "
    """
    score = 0
    for cluster_id in solution:    # cluster or clique
        clusterActivities = solution[cluster_id]
        score += sum(weights[i][j] for i in clusterActivities for j in clusterActivities if i != j)

    score_excl_penalties = score
    no_unassigned_activities = 0
    # for each activity in a cluster without a gate: add large_number, because this implies that the activity is assigned to the dummy gate
    for cluster_id in solution:
        contains_gate = False
        for vertex in solution[cluster_id]:
            if contains_gate:
                continue
            is_activity_vertex = False
            for s in ["dep", "arr", "par"]:
                if vertex.startswith(s):
                    is_activity_vertex = True
            if not is_activity_vertex:
                contains_gate = True
        if not contains_gate:
            score += large_negative * len(solution[cluster_id])
            no_unassigned_activities += len(solution[cluster_id])


    return score, score_excl_penalties, no_unassigned_activities

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

def is_move_feasible_new(vertex, current_solution, current_cluster, target_cluster, shadow_constraints, flights_to_activities, activities_to_flights,
                         nodes_to_clusters):
    """
    Checks if moving flight `i` to `proposed_gate` violates any shadow constraints.
    New version that also considers situations where gate vertices are moved.
    """
    # check if vertex is a flight vertex
    is_flight_vertex = False
    for s in ["dep", "par", "arr"]:
        if vertex.startswith(s):
            is_flight_vertex = True
            break

    if is_flight_vertex:
        # get flight that is supposed to be moved and all gates in the target cluster (must be either 0 or 1)
        target_flight = activities_to_flights[vertex]
        target_gates_list = list([val for val in target_cluster if val.startswith("gate")])
        # if target cluster contains no gate: shadow restriction trivially satisfied
        if len(target_gates_list) == 0:
            return True
        # if target cluster contains more than 1 gate: raise an error (this should never happen)
        if len(target_gates_list) > 1:
            raise Exception(f"Target cluster contains more than one gate!")
        # else: get name of target gate
        else:
            target_gate = target_gates_list[0]

        # check all relevant shadow restrictions for violation
        for (f1, g1, f2, g2) in shadow_constraints:
            # only need to consider shadow constraints where the target flight is assigned to the target gate
            is_relevant = False
            if (f1, g1) == (target_flight, target_gate):
                other_flight, other_gate = f2, g2
                is_relevant = True
            elif (f2, g2) == (target_flight, target_gate):
                other_flight, other_gate = f1, g1
                is_relevant = True
            if is_relevant:
                # check if other_flight is assigned to other_gate. If this is the case: constraint violated -> return False
                for activity in flights_to_activities[other_flight]:
                    if nodes_to_clusters[activity] == nodes_to_clusters[other_gate]:
                        return False


    # if vertex is not a flight vertex: need to check for all possible shadow restrictions involving gate 'vertex'
    else:
        relevant_constraints = []
        for (f1, g1, f2, g2) in shadow_constraints:
            # only need to consider shadow constraints where the target flight is assigned to the target gate
            is_relevant = False
            if g1 == vertex:
                own_flight = f1
                other_flight, other_gate = f2, g2
                is_relevant = True
            elif g2 == vertex:
                own_flight = f2
                other_flight, other_gate = f1, g1
                is_relevant = True
            if is_relevant:
                # check if other_flight is assigned to other_gate and own_flight is assigned to vertex. If True -> constraint is violated
                for other_activity in flights_to_activities[other_flight]:
                    for own_activity in flights_to_activities[own_flight]:
                        if nodes_to_clusters[other_activity] == nodes_to_clusters[other_gate] and nodes_to_clusters[own_activity] == nodes_to_clusters[vertex]:
                            return False



    return True


def reassign_vertices(solution, cluster_contains_gate, gates_per_cluster, weights, M_validGate, P_preferences, activities_to_flights,
                      nodes_to_clusters):
    """
    Reassign all non-mandatory dummy gate assignments.
    """
    # for each cluster: check if there are any gate inside the cluster. If not, this implies that this cluster is assigned to the dummy gate
    for cluster_id in solution:
        if solution[cluster_id] == []:  # skip empty clusters
            continue
        if not cluster_contains_gate[cluster_id]:
            for activity in solution[cluster_id]:
                # get random gate with maximum preference
                flight = activities_to_flights[activity]
                maximum_preference_gates = [gate for gate in P_preferences[flight] if P_preferences[flight][gate] == max(P_preferences[flight].values())]
                target_gate = random.choice(maximum_preference_gates)
                target_cluster_id = nodes_to_clusters[target_gate]
                solution[target_cluster_id].append(activity)
                nodes_to_clusters[activity] = target_cluster_id
                # print(f"Reassigned activity {activity} from {cluster_id} to {target_cluster_id}")
            # above procedure will be executed for all activities, so cluster will eventually be empty
            solution[cluster_id] = []

    return solution, nodes_to_clusters


def eliminate_conflicts(solution, M_validGate, U_successor, activities_to_flights, flights_to_activities,
                        nodes_to_clusters, shadow_constraints, weights, large_negative):
    """
    Removes gate conflicts by reassigning conflicting flights to alternative gates or to a dummy gate if no alternatives exist.
    """

    # 1. eliminate gate conflicts
    for cluster_id in solution:
        for vertex_i in solution[cluster_id]:
            for vertex_j in solution[cluster_id]:
                if vertex_i == vertex_j:
                    continue
                if weights[vertex_i][vertex_j] == large_negative:
                    # remove vertex_j from the cluster and insert it into an empty cluster, together with all of its successors
                    if vertex_j.startswith("dep") or vertex_j.startswith("arr") or vertex_j.startswith("par"):
                        vertex_to_remove = vertex_j
                    else:       # catch the case where vertex_j is a gate (this shouldn't happen anyway, though)
                        vertex_to_remove = vertex_i
                    # find empty cluster and insert activities
                    new_cluster_found = False
                    for target_cluster_id in solution:
                        if solution[target_cluster_id] == [] and not new_cluster_found:
                            new_cluster_found = True
                            solution[target_cluster_id] = flights_to_activities[activities_to_flights[vertex_to_remove]].copy()
                            for act in flights_to_activities[activities_to_flights[vertex_to_remove]]:
                                solution[nodes_to_clusters[act]].remove(act)
                                nodes_to_clusters[act] = target_cluster_id
                    if not new_cluster_found:
                        raise Exception("No empty cluster found")


    # 2. eliminate shadow constraints
    for (f1, g1, f2, g2) in shadow_constraints:
        # if shadow constraint is violated: assign all activities associated with flight 1 into an empty cluster
        for act1 in flights_to_activities[f1]:
            for act2 in flights_to_activities[f2]:
                if nodes_to_clusters[act1] == nodes_to_clusters[g1] and nodes_to_clusters[act2] == nodes_to_clusters[g2]:
                    activities = flights_to_activities[f1]
                    # remove activities from existing clusters
                    for act in activities:
                        solution[nodes_to_clusters[act]].remove(act)
                    # find an empty cluster and insert all relevant activities
                    new_cluster_found = False
                    for cluster_id in solution:
                        if solution[cluster_id] == [] and not new_cluster_found:
                            solution[cluster_id] = activities.copy()
                            for act in activities:
                                nodes_to_clusters[act] = cluster_id
                            new_cluster_found = True
                    if not new_cluster_found:
                        raise Exception("No empty cluster found")

    print("Finished eliminating all gate and shadow conflicts.")

    return solution, nodes_to_clusters


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
    t1 = time.time()

    activities = list(activities_to_flights.keys())     # ['arr_1', 'dep_1', ...]
    gates = list(gates_to_indices.keys())               # ['120', '122', ...]
    # 0. create initially empty clusters, one for each node in the graph (=activities and gates EXCL. the dummy gate)
    clusters = {}   # keys = cluster_idx, values = list of nodes inside the cluster
    nodes_to_clusters = {} # keys = node names (activities, gates), values = name of cluster to which node belongs
    it = 1
    for gate in gates:
        clusters[f"cluster_{it}"] = [gate]
        nodes_to_clusters[gate] = f"cluster_{it}"
        it += 1
    for act in activities:
        clusters[f"cluster_{it}"] = [act]
        nodes_to_clusters[act] = f"cluster_{it}"
        it += 1



    '''
    for non_tabu_Activities, paper says U(i) != 0 and U(U(i)) != 0 means arrival, but we have some arrivals for whom their departure has no successor
    -> commented lines should be used for the paper, but uncommented lines are used for our specific instance
    '''
    # non_tabu_Activities = [i for i in C_list if (U_successor[i] !=0 and U_successor[U_successor[i]] != 0)]
    non_tabu_Activities = [activity for activity in activities if activity.startswith("arr")]
    non_tabu = len(non_tabu_Activities)

    while non_tabu > 0:
        best_improvement = -np.inf
        best_target_cluster_id = None

        act = non_tabu_Activities[0]
        current_cluster = clusters[nodes_to_clusters[act]]

        # for each cluster: calculate benefit of moving activity+successors to cluster
        for cluster_id in clusters:
            target_cluster = clusters[cluster_id]
            h1 = calculate_heuristic_value(act, current_cluster, target_cluster, weights, activities_to_flights, gates_to_indices)
            h2 = calculate_heuristic_value(U_successor[act], current_cluster, target_cluster, weights, activities_to_flights, gates_to_indices)
            if U_successor[U_successor[act]] != 0:
                h3 = calculate_heuristic_value(U_successor[U_successor[act]], current_cluster, target_cluster, weights, activities_to_flights, gates_to_indices)
            else:
                h3 = 0

            improvement = h1 + h2 + h3
            # if improvement is best found so far: save it!
            if improvement > best_improvement:
                best_improvement = improvement
                best_target_cluster_id = cluster_id

        # if there is a feasible improving move: move activity+successors to respective cluster, otherwise keep everything and mark activity as tabu
        if best_improvement > 0:
            successor = U_successor[act]
            succ_successor = U_successor[U_successor[act]]
            # add activities to new cluster
            clusters[best_target_cluster_id].extend([act, successor])
            if succ_successor != 0:
                clusters[best_target_cluster_id].extend([succ_successor])
            # remove activities from old clusters and save new cluster IDs for all relevant activities
            clusters[nodes_to_clusters[act]].remove(act)
            clusters[nodes_to_clusters[successor]].remove(successor)
            nodes_to_clusters[act] = best_target_cluster_id
            nodes_to_clusters[U_successor[act]] = best_target_cluster_id
            if succ_successor != 0:
                clusters[nodes_to_clusters[succ_successor]].remove(succ_successor)
                nodes_to_clusters[succ_successor] = best_target_cluster_id


        del non_tabu_Activities[0]
        non_tabu -= 1


    print(f"Found an initial solution. Runtime: {time.time()-t1}")
    return clusters, nodes_to_clusters

def refine_clusters(current_solution, nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                         activities_to_flights, gates_to_indices, large_negative):
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
    current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(current_solution, weights, large_negative)
    values_per_iterator = {0: current_score}  # keys = iterators r of the algorithm, values = obj. value of solution at r-th iteration
    solutions_per_iterator = {0: copy.deepcopy(current_solution)}       # keys = iterators r of the algorithm, values = solution after performing r-th iteration
    nodes_to_clusters_per_iterator = {0: copy.deepcopy(nodes_to_clusters)}

    nontabu_vertices = list(activities_to_flights.keys()) + list(gates_to_indices.keys())
    can_improve_more = True

    vertex_is_gate = {}         # keys = vertex names, values = binary indicating if vertex is a gate vertex
    cluster_contains_gate = {}      # keys = cluster IDs , values = binary indicating if cluster already contains a gate vertex (used to shorten runtime of improvement step)
    gates_per_cluster = {}
    for cluster_id in current_solution:
        contains_gate = False
        gates_per_cluster[cluster_id] = []
        for vertex in current_solution[cluster_id]:
            vertex_is_gate[vertex] = False
            is_activity_vertex = False
            for s in ["dep", "arr", "par"]:
                if vertex.startswith(s):
                    is_activity_vertex = True
            if not is_activity_vertex:
                contains_gate = True
                vertex_is_gate[vertex] = True
                gates_per_cluster[cluster_id].append(vertex)
        cluster_contains_gate[cluster_id] = contains_gate


    solution_iterator = 0       # index of the currently found solution (0=initial solution)
    maximum_move_count = 100
    while can_improve_more:
        current_solution = solutions_per_iterator[solution_iterator]     # get current solution
        nodes_to_clusters = nodes_to_clusters_per_iterator[solution_iterator]
        current_no_tabu_vertices = len(nontabu_vertices)        # used to check if any improving moves have been found in the current iteration

        # for each vertex: find the best move that leads to a feasible neighbour
        for vertex in nontabu_vertices:
            current_cluster_id = nodes_to_clusters[vertex]
            best_target_cluster_id = None
            best_improvement = large_negative       # need to make sure that infeasible moves (->overlaps) are skipped

            # for each cluster: check if move would be feasible and how objective function would change
            for target_cluster_id in current_solution:
                if target_cluster_id == nodes_to_clusters[vertex]: # skip moving vertex to its current cluster
                    continue
                # skip move evaluation of gates to clusters that already contain a gate (for runtime improvement)
                if vertex_is_gate and cluster_contains_gate[target_cluster_id]:
                    continue
                # else: evaluate improvement
                potential_improvement = calculate_heuristic_value(vertex, current_solution[current_cluster_id], current_solution[target_cluster_id],
                                                                  weights, activities_to_flights, gates_to_indices)
                # if improvement is better than the best one found so far: check for feasibility
                if potential_improvement > best_improvement:
                    # 1. check for shadow restrictions (if vertex is not a gate vertex)
                    move_allowed = is_move_feasible_new(vertex, current_solution, current_solution[current_cluster_id], current_solution[target_cluster_id],
                                                        shadow_constraints, flights_to_activities, activities_to_flights,
                                                        nodes_to_clusters)
                    # 2. if target cluster is empty: current cluster needs to contain at least 2 elements
                    if len(current_solution[target_cluster_id]) == 0 and len(current_solution[current_cluster_id]) == 1:
                        move_allowed = False
                    # if move is feasible: remember this as the best possible move
                    if move_allowed:
                        best_target_cluster_id = target_cluster_id
                        best_improvement = potential_improvement

            # if a feasible, improving move has been found: perform it and store it
            if best_improvement > large_negative and best_target_cluster_id is not None:
                # copy solution
                target_solution = copy.deepcopy(current_solution)
                # move vertex to its new cluster and update its assigned cluster id
                target_solution[current_cluster_id].remove(vertex)
                target_solution[best_target_cluster_id].append(vertex)
                target_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)
                target_nodes_to_clusters[vertex] = best_target_cluster_id
                # mark vertex as tabu
                nontabu_vertices.remove(vertex)
                # save solution value and solution itself
                solution_iterator += 1
                values_per_iterator[solution_iterator] = values_per_iterator[solution_iterator - 1] + best_improvement
                solutions_per_iterator[solution_iterator] = target_solution
                nodes_to_clusters_per_iterator[solution_iterator] = target_nodes_to_clusters
                # print(f"Found an improving move. Moving vertex {vertex} from {current_cluster_id} to {best_target_cluster_id}."
                #       f"Improvement: {best_improvement}. Current solution iterator: {solution_iterator}, value: {values_per_iterator[solution_iterator]}")
                # if vertex that has been moved is a gate vertex: remember that target cluster now has a gate!
                if vertex_is_gate[vertex]:
                    cluster_contains_gate[best_target_cluster_id] = True
                    cluster_contains_gate[current_cluster_id] = False
                    gates_per_cluster[best_target_cluster_id].append(vertex)
                    gates_per_cluster[current_cluster_id].remove(vertex)

            # todo remove
            if solution_iterator > maximum_move_count:
                can_improve_more = False
                break
            # todo

        # if no improving moves have been found in the whole iteration: terminate to prevent cycling
        if len(nontabu_vertices) == current_no_tabu_vertices:
            can_improve_more = False


    # get iteration where objective value has been maximal
    values_sorted = dict(sorted(values_per_iterator.items(), key = lambda x: x[1], reverse=True))
    best_iterator = list(values_sorted.keys())[0]
    best_solution = solutions_per_iterator[best_iterator]
    best_nodes_to_clusters = nodes_to_clusters_per_iterator[best_iterator]
    print(f"Best solution found at iteration {best_iterator}, value: {values_sorted[best_iterator]}")

    return best_solution, best_nodes_to_clusters, cluster_contains_gate, gates_per_cluster



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
                    current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(solution, weights, large_negative)
                    # Swap back to undo
                    solution[i], solution[j] = solution[j], solution[i]
                    new_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(solution, weights, large_negative)

                    # If the new configuration is better, accept the swap permanently
                    if new_score < current_score:
                        solution[i], solution[j] = solution[j], solution[i]
                        improved = True
    return solution


def iterative_refinement_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                           shadow_constraints, num_flights,
                                           activities_to_flights, gates_to_indices, flights_to_activities,
                                           large_negative):
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
    current_solution, nodes_to_clusters = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    # best_solution = refine_clusters(current_solution, nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
    #                 activities_to_flights, gates_to_indices, large_negative)
    best_score = -np.inf
    # print("Initial best solution and score from refinement:", best_solution, best_score)

    run_count = 0
    print("\n\n")
    while run_count < 7:
        print(f"Starting iteration. Value of current solution: {calculate_total_score(current_solution, weights, large_negative)[0]}")
        refined_solution, nodes_to_clusters, cluster_contains_gate, gates_per_cluster = refine_clusters(current_solution, nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                    activities_to_flights, gates_to_indices, large_negative)
        current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)
        print(f"Algorithm 2 terminated. Value of solution: {current_score}. Re-assigning and eliminating conflicts now...")

        if current_score == best_score:
            print("No improvement in solution; terminating the process.")
            break  # Terminate the process if no improvement is found

        elif current_score > best_score:
            best_solution = copy.deepcopy(refined_solution)
            best_score = current_score
            run_count = 0  # Reset the run count if improvement is found
            print("New best solution found, score updated:", best_score)

        else:
            run_count += 1  # Increment run count if no improvement

        # reassign unassigned activities
        refined_solution, nodes_to_clusters = reassign_vertices(refined_solution, cluster_contains_gate, gates_per_cluster, weights, M_validGate, P_preferences,
                                     activities_to_flights, nodes_to_clusters)
        re_score, re_score_excl_penalties, re_no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)
        print(f"Value after reassignining unassigned activities: {re_score}.")

        # Handle any conflicts in the solution
        refined_solution, nodes_to_clusters = eliminate_conflicts(refined_solution, M_validGate, U_successor, activities_to_flights, flights_to_activities,
                            nodes_to_clusters, shadow_constraints, weights, large_negative)
        current_solution = copy.deepcopy(refined_solution)
        el_score, el_score_excl_penalties, el_no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)
        print(f"[Final] Value after eliminating conflicts: {el_score}, excluding penalties: {el_score_excl_penalties}. No. unassigned activities: {el_no_unassigned_activities}")
        print(f"Value of current best solution: {best_score}")
        print("------------------------")

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
    best_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(best_solution, weights, large_negative)

    run_count = 0
    while run_count < 7:
        # Apply a 2-opt step to refine the solution further by examining pairs of activities
        two_opt_refined_solution = apply_two_opt_step(current_solution, weights, U_successor)
        refined_solution = refine_clusters(two_opt_refined_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)

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
    best_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(best_solution, weights, large_negative)

    # Further refinement loop
    run_count = 0
    while run_count < 7:
        refined_solution = refine_clusters(best_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)

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