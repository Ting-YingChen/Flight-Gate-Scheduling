import numpy as np
import time
import copy
import random

def calculate_heuristic_value(i, C, D, weights, activities_to_flights, gates_to_indices):
    """ Calculate the heuristic value for moving vertex i from its current cluster C[i] to a new cluster D """
    # C = current cluster (list of all vertices of that cluster)
    # D = new (possibly empty) cluster (list of the vertices of that cluster)

    # sum_weights_new_cluster = sum(weights[i][j] for j in D if j != 'Dum')
    # sum_weights_current_cluster = sum(weights[i][j] for j in C if (j != i and j != 'Dum'))

    sum_weights_new_cluster = sum(weights[i][j] for j in D)
    sum_weights_current_cluster = sum(weights[i][j] for j in C if (j != i))

    return sum_weights_new_cluster - sum_weights_current_cluster

def calculate_total_score(solution, weights, large_negative):
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
            if not vertex_is_act(vertex): #to check if the vertex is an activity
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

def vertex_is_act(vertex):
    for s in ["arr", "dep", "par"]:
        if vertex.startswith(s):
            return True
    return False

def is_move_feasible_new(vertex, current_solution, current_cluster, target_cluster, shadow_constraints, flights_to_activities, activities_to_flights,
                         nodes_to_clusters, sc_per_act_gate_pair, sc_per_gate):
    """
    Checks if moving flight `i` to `proposed_gate` violates any shadow constraints.
    New version that also considers situations where gate vertices are moved.
    """
    # check if vertex is a flight vertex
    is_flight_vertex = vertex_is_act(vertex)    # True if vertex is activity, false if not (if vertex is gate)

    if is_flight_vertex:
        # get flight that is supposed to be moved and all gates in the target cluster (must be either 0 or 1)
        target_activity = vertex
        target_gates_list = list([vtx for vtx in target_cluster if vertex_is_act(vtx) == False])  # A list of gates in the target cluster
        # if target cluster contains no gate: shadow restriction trivially satisfied
        if len(target_gates_list) == 0:
            return True
        # if target cluster contains more than 1 gate: raise an error (this should never happen)
        if len(target_gates_list) > 1:
            raise Exception(f"Target cluster contains more than one gate!")
        # else: get name of target gate
        else:
            target_gate = target_gates_list[0]

        # check all relevant shadow restrictions for violation*
        if (target_activity, target_gate) in sc_per_act_gate_pair: # *if there are any
            for (a2, g2) in sc_per_act_gate_pair[(target_activity, target_gate)]:
                if nodes_to_clusters[a2] == nodes_to_clusters[g2]:
                    return False

    # if vertex is not a flight vertex: need to check for all possible shadow restrictions involving gate 'vertex'
    elif vertex in sc_per_gate:    # If the gate has any shadow constraints at all
        relevant_constraints = []  # get all shadow constraints involving this gate.
        for (a1, a2, g2) in sc_per_gate[vertex]:
            own_flight = activities_to_flights[a1]
            other_flight = activities_to_flights[a2]
            other_gate = g2

            # Check Shadow Constraints for the Gate
            for other_activity in flights_to_activities[other_flight]:
                for own_activity in flights_to_activities[own_flight]:
                    if nodes_to_clusters[other_activity] == nodes_to_clusters[other_gate] and nodes_to_clusters[
                        own_activity] == nodes_to_clusters[vertex]:
                        return False

    return True

def reassign_vertices(solution, cluster_contains_gate, cluster_to_gates, weights, M_validGate, P_preferences, activities_to_flights,
                      nodes_to_clusters):
    """
    Reassign all non-mandatory dummy gate assignments.
    """
    # for each cluster: check if there are any gate inside the cluster. If not, this implies that this cluster is assigned to the dummy gate
    for cluster_id in solution:
        if solution[cluster_id] == []:  # skip empty clusters
            continue
        if not cluster_contains_gate[cluster_id]:  # If the cluster does not contain a gate
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

    # 1. eliminate gate conflicts, i.e. overlaping gates on same cluster (gate)
    for cluster_id in solution:
        for vertex_i in solution[cluster_id]:
            for vertex_j in solution[cluster_id]:
                if vertex_i == vertex_j:
                    continue
                if weights[vertex_i][vertex_j] == large_negative:   # i.e. they overlap
                    # remove vertex_j from the cluster and insert it into an empty cluster, together with all of its successors
                    if vertex_is_act(vertex_j):
                        vertex_to_remove = vertex_j
                    else:       # catch the case where vertex_j is a gate (this shouldn't happen anyway, though)
                        vertex_to_remove = vertex_i
                    # find empty cluster and insert activities
                    new_cluster_found = False
                    for target_cluster_id in solution:
                        if solution[target_cluster_id] == [] and not new_cluster_found:
                            new_cluster_found = True
                            allAct_SameFlight = flights_to_activities[activities_to_flights[vertex_to_remove]]
                            solution[target_cluster_id] = allAct_SameFlight.copy()  # Assign these activities to the empty cluster
                            for act in allAct_SameFlight:
                                solution[nodes_to_clusters[act]].remove(act)  # Remove activities from their original cluster
                                nodes_to_clusters[act] = target_cluster_id  # Update new cluster assignment
                    if not new_cluster_found:
                        raise Exception("No empty cluster found")


    # 2. eliminate shadow constraints
    for (a1, g1, a2, g2) in shadow_constraints:
        f1 = activities_to_flights[a1]  # Get the flight associated with activities a1.
        f2 = activities_to_flights[a2]
        # if shadow constraint is violated: assign all activities associated with flight 1 into an empty cluster
        for act1 in flights_to_activities[f1]:
            for act2 in flights_to_activities[f2]:
                if nodes_to_clusters[act1] == nodes_to_clusters[g1] and nodes_to_clusters[act2] == nodes_to_clusters[g2]:
                    activities = flights_to_activities[f1]  # Get all activities associated with flight f1.
                    # remove activities from existing clusters
                    for act in activities:
                        solution[nodes_to_clusters[act]].remove(act)  # Find the current cluster of act, remove act
                    # find an empty cluster and insert all relevant activities
                    new_cluster_found = False
                    for cluster_id in solution:
                        if solution[cluster_id] == [] and not new_cluster_found:
                            solution[cluster_id] = activities.copy()
                            for act in activities:
                                nodes_to_clusters[act] = cluster_id  # update assignment
                            new_cluster_found = True
                    if not new_cluster_found:
                        raise Exception("No empty cluster found")

    print("~Finished eliminating all gate and shadow conflicts~")

    return solution, nodes_to_clusters

def initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor):
    """(Algorithm 2)"""
    t1 = time.time()

    activities = list(activities_to_flights.keys())     # ['arr_1', 'dep_1', ...]
    gates = list(gates_to_indices.keys())               # ['120', '122', ...]

    # 0. create initially empty clusters, one for each node in the graph (=activities and gates EXCL. the dummy gate)
    clusters = {}   # keys = cluster_idx, values = list of nodes inside the cluster
    nodes_to_clusters = {} # keys = node names (activities, gates), values = name of cluster to which node belongs
    it = 1
    for gate in gates:
        clusters[f"cluster_{it}"] = [gate]  # Create a new cluster with cluster_{it}, assign the gate to this cluster
        nodes_to_clusters[gate] = f"cluster_{it}"  # Update gate-cluster assignment
        it += 1
    for act in activities:
        clusters[f"cluster_{it}"] = [act]
        nodes_to_clusters[act] = f"cluster_{it}"
        it += 1

    non_tabu_Activities = [activity for activity in activities if activity.startswith("arr")]
    non_tabu = len(non_tabu_Activities)

    while non_tabu > 0:
        best_improvement = -np.inf
        best_target_cluster_id = None

        act = non_tabu_Activities[0]  # act is set to the first activity in the list of non-tabu activities
        current_cluster = clusters[nodes_to_clusters[act]]

        # for each cluster: calculate benefit of moving activity+successors to cluster
        for cluster_id in clusters:
            target_cluster = clusters[cluster_id]
            h1 = calculate_heuristic_value(act, current_cluster, target_cluster, weights, activities_to_flights, gates_to_indices)
            h2 = calculate_heuristic_value(U_successor[act], current_cluster, target_cluster, weights, activities_to_flights, gates_to_indices)
            if U_successor[U_successor[act]] != 0:  # the successor of successor
                h3 = calculate_heuristic_value(U_successor[U_successor[act]], current_cluster, target_cluster, weights, activities_to_flights, gates_to_indices)
            else:
                h3 = 0

            improvement = h1 + h2 + h3
            if improvement > best_improvement:  # if improvement is best found so far: save it!
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

    print(f"Found an initial solution. Runtime: {time.time()-t1} seconds.")

    return clusters, nodes_to_clusters

def refine_clusters(current_solution, nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                         activities_to_flights, gates_to_indices, large_negative, sc_per_act_gate_pair, sc_per_gate):
    """(Algorithm 1)"""

    # Initialization
    current_score, score_excl_penalties, initial_no_unassigned_activities = calculate_total_score(current_solution, weights, large_negative)
    values_per_iterator = {0: current_score}  # keys = iterators r of the algorithm, values = obj. value of solution at r-th iteration
    # solutions_per_iterator = {0: copy.deepcopy(current_solution)}       # keys = iterators r of the algorithm, values = solution after performing r-th iteration

    nontabu_vertices = list(activities_to_flights.keys())   # Only flight activities are made nontabu
    can_improve_more = True

    vertex_is_gate = {}         # keys = vertex names, values = binary indicating if vertex is a gate vertex
    cluster_contains_gate = {}      # keys = cluster IDs , values = binary indicating if cluster already contains a gate vertex (used to shorten runtime of improvement step)
    cluster_to_gates = {}

    # Find which clusters contain a gate
    for cluster_id in current_solution:
        contains_gate = False
        cluster_to_gates[cluster_id] = []
        for vertex in current_solution[cluster_id]:
            vertex_is_gate[vertex] = not vertex_is_act(vertex)
            # is_activity_vertex = False
            if not vertex_is_act(vertex):
                contains_gate = True
                cluster_to_gates[cluster_id].append(vertex)
        cluster_contains_gate[cluster_id] = contains_gate

    solution_data_per_iterator = {0: (copy.deepcopy(current_solution), copy.deepcopy(nodes_to_clusters),
                                      copy.deepcopy(cluster_contains_gate), copy.deepcopy(cluster_to_gates))}

    solution_iterator = 0       # index of the currently found solution (0=initial solution)
    maximum_move_count = 50000      # large number that should never be reached
    while can_improve_more:
        current_solution, nodes_to_clusters, cluster_contains_gate, cluster_to_gates = solution_data_per_iterator[solution_iterator]
        current_no_tabu_vertices = len(nontabu_vertices)        # used to check if any improving moves have been found in the current iteration

        # for each vertex: find the best move that leads to a feasible neighbour
        for vertex in nontabu_vertices:
            current_cluster_id = nodes_to_clusters[vertex]
            best_target_cluster_id = None
            best_score = current_score

            # for each cluster: check if move would be feasible and how objective function would change
            for target_cluster_id in current_solution:
                if target_cluster_id == nodes_to_clusters[vertex]: # skip moving vertex to its current cluster
                    continue
                # need to make sure that infeasible moves (->overlaps) are skipped
                # forbid moving the vertex to a cluster where it will overlap with 1 or more activities
                for activity in current_solution[target_cluster_id]:
                    if weights[vertex][activity] <0:
                        continue
                        '''Does this continue affect the previous for (as it should) or this for?'''
                # # skip move evaluation of gates to clusters that already contain a gate (for runtime improvement)
                # if vertex_is_gate[vertex] and cluster_contains_gate[target_cluster_id]:
                #     continue
                # else: evaluate improvement and amount of unassigned gates
                potential_score = calculate_heuristic_value(vertex, current_solution[current_cluster_id], current_solution[target_cluster_id],
                                                                  weights, activities_to_flights, gates_to_indices)
                # if improvement is better than the best one found so far: check for feasibility
                if potential_score > best_score:
                    # print("--------Potential_score is higher")
                    # 1. check for shadow restrictions (if vertex is not a gate vertex)
                    move_allowed = is_move_feasible_new(vertex, current_solution, current_solution[current_cluster_id], current_solution[target_cluster_id],
                                                        shadow_constraints, flights_to_activities, activities_to_flights,
                                                        nodes_to_clusters, sc_per_act_gate_pair, sc_per_gate)

                    # 2. if target cluster is empty: current cluster needs to contain at least 2 elements
                    if len(current_solution[target_cluster_id]) == 0 and len(current_solution[current_cluster_id]) == 2:
                        move_allowed = False
                    # # 3. (Arthur) if target cluster has no gate (activitiy would go to dummy gate), then move not allowed
                    # if cluster_contains_gate[target_cluster_id] == False:
                    #     move_allowed = False
                    # if move is feasible: remember this as the best possible move
                    if move_allowed:
                        best_target_cluster_id = target_cluster_id
                        best_score = potential_score

            # if a feasible and improving move has been found: perform it and store it
            # improvingMove = best_improvement > large_negative
            move_is_improving = best_score > current_score
            move_exists = best_target_cluster_id is not None
            if move_is_improving and move_exists:
                target_solution = copy.deepcopy(current_solution)
                # move vertex to its new cluster and update its assigned cluster id
                target_solution[current_cluster_id].remove(vertex)
                target_solution[best_target_cluster_id].append(vertex)
                target_no_unassigned_activities = calculate_total_score(target_solution, weights, large_negative)[2]

                # Check if there are now more unassigned activities -> if yes, reverse the action and continue to next for iteration
                if target_no_unassigned_activities > initial_no_unassigned_activities:
                    target_solution[current_cluster_id].append(vertex)
                    target_solution[best_target_cluster_id].remove(vertex)
                    continue
                target_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)
                target_nodes_to_clusters[vertex] = best_target_cluster_id
                target_cluster_contains_gate = copy.deepcopy(cluster_contains_gate)
                target_cluster_to_gates = copy.deepcopy(cluster_to_gates)

                # mark vertex as tabu
                nontabu_vertices.remove(vertex)
                # save solution value and solution itself
                solution_iterator += 1
                # values_per_iterator[solution_iterator] = values_per_iterator[solution_iterator - 1] + best_score
                values_per_iterator[solution_iterator] = best_score
                # print(f"Found an improving move. Moving vertex {vertex} from {current_cluster_id} to {best_target_cluster_id}."
                #       f"Improvement: {best_improvement}. Current solution iterator: {solution_iterator}, value: {values_per_iterator[solution_iterator]}")
                # if vertex that has been moved is a gate vertex: remember that target cluster now has a gate!
                if vertex_is_gate[vertex]:
                    target_cluster_contains_gate[best_target_cluster_id] = True
                    target_cluster_contains_gate[current_cluster_id] = False
                    target_cluster_to_gates[best_target_cluster_id].append(vertex)
                    target_cluster_to_gates[current_cluster_id].remove(vertex)
                solution_data_per_iterator[solution_iterator] = (target_solution, target_nodes_to_clusters, target_cluster_contains_gate, target_cluster_to_gates)

            # todo remove
            if solution_iterator > maximum_move_count:
                can_improve_more = False
                break

        # if no improving moves have been found in the whole iteration: terminate to prevent cycling
        if len(nontabu_vertices) == current_no_tabu_vertices:
            can_improve_more = False

    # get iteration where objective value has been maximal
    values_sorted = dict(sorted(values_per_iterator.items(), key = lambda x: x[1], reverse=True))
    best_iterator = list(values_sorted.keys())[0]
    best_solution, best_nodes_to_clusters, best_cluster_contains_gate, best_cluster_to_gates = solution_data_per_iterator[best_iterator]
    print(f"~Best reassignment solution found at {best_iterator}th iteration~")

    return best_solution, best_nodes_to_clusters, best_cluster_contains_gate, best_cluster_to_gates

def suboptimalGates_and_towing(solution, flights_to_activities, activities_to_flights, nodes_to_clusters):
    suboptimal_gates = []
    towings = []

    # Iterate over each cluster in the solution
    for cluster in solution:
        for vertex in cluster:

            # Check if vertex is a gate
            if not vertex_is_act(vertex):
                gate = vertex

                # Check if gate is necessarily remote (e.g., gate[0] not 1 or 2)
                if gate[0] != 1 and gate[0] != 2:
                    suboptimal_gates.append(gate)
            else: # vertex = activity
                # Process when vertex is an activity
                flight = activities_to_flights[vertex]
                flight_is_towed = False
                # Check all activities related to this flight
                otherActivities = flights_to_activities[flight]

                for otherActivity in otherActivities:
                    if nodes_to_clusters[otherActivity] != cluster: # if otherActivity is not in same cluster
                        flight_is_towed = True
                        break

                # If any related activity is not in the same cluster, mark the flight as towed
                if flight_is_towed:
                    towings.append(flight)

    return suboptimal_gates, towings

def get_related_activities(vertex, activities_to_flights, current_solution):
    # Placeholder function: implement based on current data structure
    flight = activities_to_flights[vertex]
    return [v for v, f in activities_to_flights.items() if f == flight and v != vertex]

def apply_two_opt_step(current_solution, nodes_to_clusters, weights, large_negative, activities_to_flights, M_validGate):
    """Applies a 2-opt algorithm to ..."""

    initial_score, _, _ = calculate_total_score(current_solution, weights, large_negative)
    best_solution = copy.deepcopy(current_solution)
    best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)
    best_score = initial_score
    improved = False

    vertex_is_gate = {}  # keys = vertex names, values = binary indicating if vertex is a gate vertex
    cluster_contains_gate = {}  # keys = cluster IDs , values = binary indicating if cluster already contains a gate vertex (used to shorten runtime of improvement step)

    # Initialize vertex_is_gate and cluster_contains_gate dictionaries
    gate_per_cluster = {}
    for cluster_id in current_solution:
        gate_per_cluster[cluster_id] = None
        contains_gate = False
        for vertex in current_solution[cluster_id]:
            vertex_is_gate[vertex] = not vertex_is_act(vertex)
            if not vertex_is_act(vertex):
                contains_gate = True
                gate_per_cluster[cluster_id] = vertex
        cluster_contains_gate[cluster_id] = contains_gate

    # Attempt swaps between all pairs of vertices not in the same cluster
    activity_vertices = [vertex for vertex in vertex_is_gate if
                         vertex_is_gate[vertex] == False]  # Filter only activity vertices

    # todo: only check swap quality if both vertices corresponding to activities for which not all 3 activities are already at the same gate
    # Function to check if all related activities are at the same gate
    def all_activities_same_gate(vertex, current_solution, nodes_to_clusters):
        related_activities = get_related_activities(vertex, activities_to_flights, current_solution)
        gate_set = {nodes_to_clusters[act] for act in related_activities if act in nodes_to_clusters}
        return len(gate_set) == 1

    for i in range(len(activity_vertices)):
        vertex_a = activity_vertices[i]
        flight_a = activities_to_flights[vertex_a]
        cluster_a_id = nodes_to_clusters[vertex_a]

        for j in range(i, len(activity_vertices)):  # ensure each pair is only checked once
            vertex_b = activity_vertices[j]
            flight_b = activities_to_flights[vertex_b]
            cluster_b_id = nodes_to_clusters[vertex_b]

            if cluster_a_id == cluster_b_id:
                continue

            # skip if 2-opt step would assign activities to infeasible gates, as this can not be an improving step
            if gate_per_cluster[cluster_b_id] not in M_validGate[flight_a] or gate_per_cluster[cluster_a_id] not in M_validGate[flight_b]:
                continue

            # Only attempt swaps if not all related activities are already at the same gate
            if all_activities_same_gate(vertex_a, current_solution, nodes_to_clusters) and all_activities_same_gate(vertex_b, current_solution, nodes_to_clusters):
                continue
            # Perform the swap
            current_solution[cluster_a_id].remove(vertex_a)
            current_solution[cluster_b_id].remove(vertex_b)
            current_solution[cluster_a_id].append(vertex_b)
            current_solution[cluster_b_id].append(vertex_a)

            # Update the mapping after swap
            nodes_to_clusters[vertex_a] = cluster_b_id
            nodes_to_clusters[vertex_b] = cluster_a_id

            # Recalculate the score after the swap
            new_score, _, _ = calculate_total_score(current_solution, weights, large_negative)
            # If the new score is better, accept the swap
            if new_score > best_score:
                print(f"Improvement found! Swapping {vertex_a} and {vertex_b} between {cluster_a_id} and {cluster_b_id}")
                best_score = new_score
                best_solution = copy.deepcopy(current_solution)
                best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)
                # update local cluster_a_id variable
                cluster_a_id = nodes_to_clusters[vertex_a]
                improved = True
            else:
                # Swap back if no improvement
                current_solution[cluster_a_id].remove(vertex_b)
                current_solution[cluster_b_id].remove(vertex_a)
                current_solution[cluster_a_id].append(vertex_a)
                current_solution[cluster_b_id].append(vertex_b)

                # Revert the mapping after swap back
                nodes_to_clusters[vertex_a] = cluster_a_id
                nodes_to_clusters[vertex_b] = cluster_b_id

    return improved, best_solution, best_nodes_to_clusters


def iterative_refinement_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                           shadow_constraints, num_flights,
                                           activities_to_flights, gates_to_indices, flights_to_activities,
                                           large_negative, sc_per_act_gate_pair, sc_per_gate):
    ''' Algorithm 3 '''


    # Algorithm 2
    current_solution, nodes_to_clusters = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_score = calculate_total_score(current_solution, weights, large_negative)[0]
    best_score0 = best_score
    best_solution = copy.deepcopy(current_solution)     # Otherwise while loop always runs with current solution
    best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)   # Otherwise nodes_to_clusters is modified

    limited_run_count = 0
    run_count = 1
    while limited_run_count < 7:
        print(f"\n================================ Run n°{run_count} ================================\n"
              f"Starting new run. Value of current solution: {readable_score(best_score)}")

        # Algorithm 1: refining clusters
        refined_solution, refined_nodes_to_clusters, cluster_contains_gate, cluster_to_gates = (
            refine_clusters(best_solution, best_nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints,
                            flights_to_activities, activities_to_flights, gates_to_indices, large_negative,
                            sc_per_act_gate_pair, sc_per_gate))
        score_alg1, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)
        print(f" • Algorithm 1 (refinement) terminated. Value of solution: {readable_score(score_alg1)}"
              f" ({readable_score(score_alg1-best_score0)} better than the initial value.)")
        suboptimal_gates, towings = suboptimalGates_and_towing(refined_solution, flights_to_activities,
                                                           activities_to_flights, nodes_to_clusters)
        print(f"Post-refinement: {len(suboptimal_gates)} suboptimal gate assignments, {len(towings)} towings required.")

        if score_alg1 == best_score:
            print("No improvement in solution; terminating the process.")
            # best_solution = copy.deepcopy(current_solution)
            break  # Terminate the process if no improvement is found

        elif score_alg1 > best_score:
            best_solution = copy.deepcopy(refined_solution)
            best_nodes_to_clusters = copy.deepcopy(refined_nodes_to_clusters)
            best_score = score_alg1
            limited_run_count = 0  # Reset the limit run count if improvement is found
            run_count +=1
            # print("New best solution found, score updated:", readable_score(best_score))
            suboptimal_gates, towings = suboptimalGates_and_towing(best_solution, flights_to_activities,
                                                               activities_to_flights, nodes_to_clusters)
            print(f"New best solution: {len(suboptimal_gates)} suboptimal gate assignments, {len(towings)} towings required.")


        else:
            limited_run_count += 1  # Increment limit run count if no improvement
            run_count += 1

        # Reassign unassigned activities
        reassigned_solution, reassigned_nodes_to_clusters = reassign_vertices(refined_solution, cluster_contains_gate, cluster_to_gates, weights, M_validGate, P_preferences,
                                     activities_to_flights, refined_nodes_to_clusters)
        re_score, re_score_excl_penalties, re_no_unassigned_activities = calculate_total_score(reassigned_solution, weights, large_negative)
        print(f" • Value after reassigning unassigned activities: {readable_score(re_score)}")
        suboptimal_gates, towings = suboptimalGates_and_towing(reassigned_solution, flights_to_activities,
                                                           activities_to_flights, nodes_to_clusters)
        print(f"Post-reassignment: {len(suboptimal_gates)} suboptimal gate assignments, {len(towings)} towings required.")

        # Handle any conflicts in the solution
        eliminate_solution, eliminate_nodes_to_clusters = eliminate_conflicts(reassigned_solution, M_validGate, U_successor, activities_to_flights, flights_to_activities,
                            reassigned_nodes_to_clusters, shadow_constraints, weights, large_negative)
        # current_solution = copy.deepcopy(eliminate_solution)
        el_score, el_score_excl_penalties, el_no_unassigned_activities = calculate_total_score(eliminate_solution, weights, large_negative)
        print(f" • Value after eliminating conflicts: {readable_score(el_score)} (excl. penalties: {readable_score(el_score_excl_penalties)})"
              f"\n   /!\ There are still {el_no_unassigned_activities} activities out of {num_activities} unassigned ({str(100*el_no_unassigned_activities/num_activities)[:4]}%).")
        suboptimal_gates, towings = suboptimalGates_and_towing(eliminate_solution, flights_to_activities,
                                                           activities_to_flights, nodes_to_clusters)
        print(f"Post-conflict elimination: {len(suboptimal_gates)} suboptimal gate assignments, {len(towings)} towings required.")

        print(f"   Value of current best solution: {readable_score(best_score)}\n"
              f"   Improvement/deterioration from the start by {readable_score(best_score-best_score0)} ({str((best_score-best_score0)*100/abs(best_score0))[0:7]}%)")

    return best_solution, best_score

def integrated_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                           shadow_constraints, num_flights,
                                           activities_to_flights, gates_to_indices, flights_to_activities,
                                           large_negative, sc_per_act_gate_pair, sc_per_gate):
    # Algorithm 3 + 2-opt
    current_solution, nodes_to_clusters = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_score = calculate_total_score(current_solution, weights, large_negative)[0]
    best_score0 = best_score
    best_solution = copy.deepcopy(current_solution)     # Otherwise while loop always runs with current solution
    best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)   # Otherwise nodes_to_clusters is modified

    limited_run_count = 0
    run_count = 1
    while limited_run_count < 7:
        print(f"\n================================ Run n°{run_count} ================================\n"
              f"Starting new run. Value of current solution: {readable_score(best_score)}")

        # Algorithm 1
        refined_solution, refined_nodes_to_clusters, cluster_contains_gate, cluster_to_gates = (
            refine_clusters(best_solution, best_nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints,
                            flights_to_activities, activities_to_flights, gates_to_indices, large_negative,
                            sc_per_act_gate_pair, sc_per_gate))
        score_alg1, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)
        print(f" • Algorithm 1 (refinement) terminated. Value of solution: {readable_score(score_alg1)}"
              f" ({readable_score(score_alg1-best_score0)} better than previous run)")

        if score_alg1 == best_score:
            print("No improvement in solution; terminating the process.")
            break  # Terminate the process if no improvement is found

        elif score_alg1 > best_score:
            best_solution = copy.deepcopy(refined_solution)
            best_nodes_to_clusters = copy.deepcopy(refined_nodes_to_clusters)
            best_score = score_alg1
            limited_run_count = 0  # Reset the limit run count if improvement is found
            run_count += 1

        else:
            limited_run_count += 1  # Increment limit run count if no improvement
            run_count += 1

        # Apply two-opt step
        improvement_found, two_opt_solution, two_opt_nodes_to_clusters = apply_two_opt_step(
            refined_solution, refined_nodes_to_clusters, weights, large_negative, activities_to_flights, M_validGate)

        if improvement_found:
            best_solution = copy.deepcopy(two_opt_solution)
            best_nodes_to_clusters = copy.deepcopy(two_opt_nodes_to_clusters)
            best_score = calculate_total_score(two_opt_solution, weights, large_negative)[0]
            print(f" • Two-opt step found an improvement. Value of solution: {readable_score(best_score)}")
            limited_run_count = 0  # Reset the limit run count if improvement is found
            run_count += 1
        else:
            print(f" • Two-opt step did not find an improvement. Continuing with previous best solution.")

        # Reassign unassigned activities
        reassigned_solution, reassigned_nodes_to_clusters = reassign_vertices(refined_solution, cluster_contains_gate, cluster_to_gates, weights, M_validGate, P_preferences,
                                     activities_to_flights, refined_nodes_to_clusters)
        re_score, re_score_excl_penalties, re_no_unassigned_activities = calculate_total_score(reassigned_solution, weights, large_negative)
        print(f" • Value after reassignining unassigned activities: {readable_score(re_score)}")

        # Handle any conflicts in the solution
        eliminate_solution, eliminate_nodes_to_clusters = eliminate_conflicts(reassigned_solution, M_validGate, U_successor, activities_to_flights, flights_to_activities,
                            reassigned_nodes_to_clusters, shadow_constraints, weights, large_negative)
        el_score, el_score_excl_penalties, el_no_unassigned_activities = calculate_total_score(eliminate_solution, weights, large_negative)
        print(f" • Value after eliminating conflicts: {readable_score(el_score)} (excl. penalties: {readable_score(el_score_excl_penalties)})"
              f"\n   /!\ There are still {el_no_unassigned_activities} activities out of {num_activities} ({str(100*el_no_unassigned_activities/num_activities)[:4]}%)")
        print(f"   Value of current best solution: {readable_score(best_score)}\n"
              f"   Improvement/deterioration from the start by {readable_score(best_score-best_score0)} ({str((best_score-best_score0)*100/abs(best_score0))[0:7]}%)")

    return best_solution, best_score

def pre_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                               shadow_constraints, num_flights,
                               activities_to_flights, gates_to_indices, flights_to_activities,
                               large_negative, sc_per_act_gate_pair, sc_per_gate):
    """Performs a 2-opt optimization specifically for gate assignments before any detailed refinement steps."""

    current_solution, nodes_to_clusters = initialize_clusters(weights, activities_to_flights, gates_to_indices,
                                                              U_successor)
    best_score = calculate_total_score(current_solution, weights, large_negative)[0]
    best_score0 = best_score
    best_solution = copy.deepcopy(current_solution)
    best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)

    limited_run_count = 0
    run_count = 1
    while limited_run_count < 7:
        print(f"\n================================ Run n°{run_count} ================================\n"
              f"Starting new run. Value of current solution: {readable_score(best_score)}")

        # Apply 2-opt step before any refinement to possibly find initial improvements
        improvement_found, two_opt_solution, two_opt_nodes_to_clusters = apply_two_opt_step(
            best_solution, best_nodes_to_clusters, weights, large_negative, activities_to_flights, M_validGate)

        # Update solution if improvement is found
        if improvement_found:
            best_solution = copy.deepcopy(two_opt_solution)
            best_nodes_to_clusters = copy.deepcopy(two_opt_nodes_to_clusters)
            best_score = calculate_total_score(best_solution, weights, large_negative)[0]
            print(f"2-opt improvement found: New score {best_score}")
            limited_run_count = 0  # Reset if an improvement is found
        else:
            print("No improvement found with 2-opt, proceeding with refinement.")
            limited_run_count += 1  # Increment count if no improvement

        # Refinement step to move individual activities
        refined_solution, refined_nodes_to_clusters, cluster_contains_gate, cluster_to_gates = refine_clusters(
            best_solution, best_nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints,
            flights_to_activities, activities_to_flights, gates_to_indices, large_negative,
            sc_per_act_gate_pair, sc_per_gate)
        score_alg1 = calculate_total_score(refined_solution, weights, large_negative)[0]

        print(f" • Algorithm 1 (refinement) terminated. Value of solution: {score_alg1}")

        if score_alg1 > best_score:
            print(f"Refinement improved score to {score_alg1}")
            best_solution = copy.deepcopy(refined_solution)
            best_nodes_to_clusters = copy.deepcopy(refined_nodes_to_clusters)
            best_score = score_alg1
            limited_run_count = 0
        # else:
        #     limited_run_count += 1
        run_count += 1

        # Reassign any non-optimal gate assignments and handle conflicts
        # Reassign unassigned activities
        reassigned_solution, reassigned_nodes_to_clusters = reassign_vertices(refined_solution, cluster_contains_gate,
                                                                              cluster_to_gates, weights, M_validGate,
                                                                              P_preferences,
                                                                              activities_to_flights,
                                                                              refined_nodes_to_clusters)
        re_score, re_score_excl_penalties, re_no_unassigned_activities = calculate_total_score(reassigned_solution,
                                                                                               weights, large_negative)
        print(f" • Value after reassignining unassigned activities: {readable_score(re_score)}")

        # Handle any conflicts in the solution
        eliminate_solution, eliminate_nodes_to_clusters = eliminate_conflicts(reassigned_solution, M_validGate,
                                                                              U_successor, activities_to_flights,
                                                                              flights_to_activities,
                                                                              reassigned_nodes_to_clusters,
                                                                              shadow_constraints, weights,
                                                                              large_negative)
        # current_solution = copy.deepcopy(eliminate_solution)
        el_score, el_score_excl_penalties, el_no_unassigned_activities = calculate_total_score(eliminate_solution,
                                                                                               weights, large_negative)
        print(
            f" • Value after eliminating conflicts: {readable_score(el_score)} (excl. penalties: {readable_score(el_score_excl_penalties)})"
            f"\n   /!\ There are still {el_no_unassigned_activities} activities out of {num_activities} ({str(100 * el_no_unassigned_activities / num_activities)[:4]}%)")
        print(f"   Value of current best solution: {readable_score(best_score)}\n"
              f"   Improvement/deterioration from the start by {readable_score(best_score - best_score0)} ({str((best_score - best_score0) * 100 / abs(best_score0))[0:7]}%)")


    return best_solution, best_score


def readable_score(n):
    return f"{n:,}"