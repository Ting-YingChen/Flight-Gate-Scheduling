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
            if not vertex_is_act(vertex):
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
        target_gates_list = list([vtx for vtx in target_cluster if vertex_is_act(vtx) == False])
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
        relevant_constraints = []
        for (a1, a2, g2) in sc_per_gate[vertex]:
            own_flight = activities_to_flights[a1]
            other_flight = activities_to_flights[a2]
            other_gate = g2
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

    # 1. eliminate gate conflicts, i.e. overlaping gates on same cluster (gate)
    for cluster_id in solution:
        for vertex_i in solution[cluster_id]:
            for vertex_j in solution[cluster_id]:
                if vertex_i == vertex_j:
                    continue
                if weights[vertex_i][vertex_j] == large_negative:   # i.e. the activities overlap
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
                            solution[target_cluster_id] = allAct_SameFlight.copy()
                            for act in allAct_SameFlight:
                                solution[nodes_to_clusters[act]].remove(act)
                                nodes_to_clusters[act] = target_cluster_id
                    if not new_cluster_found:
                        raise Exception("No empty cluster found")


    # 2. eliminate shadow constraints
    for (a1, g1, a2, g2) in shadow_constraints:
        f1 = activities_to_flights[a1]
        f2 = activities_to_flights[a2]
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

    print("~Finished eliminating all gate and shadow conflicts~")

    return solution, nodes_to_clusters

def find_my_cluster(activity, solution):
    for cluster_id in solution:
        for vertex in solution[cluster_id]:
            if vertex == activity:
                return cluster_id
    return None

def eliminate_conflicts_new(solution, M_validGate, U_successor, activities_to_flights, flights_to_activities,
                        nodes_to_clusters_input, shadow_constraints, weights, large_negative, P_preferences,
                            num_activities, num_gates, gates_to_indices, sc_per_act_gate_pair, sc_per_gate):
    """
    Removes gate conflicts by reassigning conflicting flights to alternative gates or to a dummy gate if no alternatives exist.
    """

    print('============= Alg3 has started =============')

    current_solution = copy.deepcopy(solution)
    best_solution = copy.deepcopy(solution)
    nodes_to_clusters = copy.deepcopy(nodes_to_clusters_input)

    run_count = 0
    while run_count < 8:
        count2 = 0
        print(f'========================== I have started a new run, run_count = {run_count} ==========================\n'
              f'========================== # of clusters = {len(current_solution)} ==========================')
        run_count += 1
        for cluster_id in current_solution:
            count2 += 1
            if count2%10 == 0 or count2 > (len(current_solution)-5):
                print(f'Working on cluster n°{count2}')
            if current_solution[cluster_id] == []:
                continue
            PossiblyGate = current_solution[cluster_id][0]  # first vertex of cluster
            if not vertex_is_act(PossiblyGate) or current_solution[cluster_id] == []:
                # -> vertex is a gate, so the corresponding activities are not assigned to the dummy gate
                # skip empty clusters
                continue
            else:
                for vertex_i in current_solution[cluster_id]: # all activities in that cluster, they are assigned to the dummy gate
                    #### 2.1 Assign i to a gate ####
                    flight = activities_to_flights[vertex_i]
                    maximum_preference_gates = [gate for gate in P_preferences[flight] if P_preferences[flight][gate] == max(P_preferences[flight].values())]
                    target_gate = random.choice(maximum_preference_gates)
                    target_cluster_id = nodes_to_clusters[target_gate]
                    current_solution[target_cluster_id].append(vertex_i)
                    nodes_to_clusters[vertex_i] = target_cluster_id
                    # print(f"Reassigned activity {activity} from {cluster_id} to {target_cluster_id}")
                    current_solution[cluster_id] = []

                    #### 2.2 Eliminate gate conflicts ####
                    for vertex_j in current_solution[target_cluster_id]:    # for all j in N: j in same clique...
                        if vertex_j != vertex_i and weights[vertex_i][vertex_j] == large_negative:  #... and w_ij = large negative
                            # find empty cluster and insert activities
                            new_cluster_found = False
                            for tci_el_g_con in current_solution:   # Target Cluster ID for Eliminating Gate Conflicts
                                if current_solution[tci_el_g_con] == [] and not new_cluster_found:
                                    new_cluster_found = True
                                    allAct_SameFlight = flights_to_activities[activities_to_flights[vertex_j]]
                                    current_solution[tci_el_g_con] = allAct_SameFlight.copy()
                                    for act in allAct_SameFlight:
                                        # if nodes_to_clusters[act] in current_solution:  # Sometimes error 'remove(x): x not in list. Not optimal but yeah for now
                                        if act != vertex_j:
                                            current_solution[find_my_cluster(act, current_solution)].remove(act)
                                        nodes_to_clusters[act] = tci_el_g_con
                            if not new_cluster_found:
                                raise Exception("Error, expection raised: no empty cluster found to eliminate GATE conflict")

                    #### 2.3 Eliminate shadow conflicts ####
                    for new_cluster in current_solution:    # Check all j's that might have a SC with i
                        if current_solution[new_cluster] == []:
                            continue
                        Gate_of_J = current_solution[new_cluster][0]  # first vertex of cluster
                        if vertex_is_act(Gate_of_J) or current_solution[new_cluster] == []:  # If cluster is empty or 'Dummy'
                            continue
                        else:
                             if (vertex_i,target_gate,vertex_j,Gate_of_J) in shadow_constraints and weights[vertex_i][vertex_j] == large_negative:
                                 # find an empty cluster and insert all relevant activities
                                 new_cluster_found = False
                                 for tci_el_sc_con in current_solution:
                                     if current_solution[tci_el_sc_con] == [] and not new_cluster_found:
                                         new_cluster_found = True
                                         activities_like_j = flights_to_activities[activities_to_flights[vertex_j]]
                                         current_solution[tci_el_sc_con] = activities_like_j.copy()
                                         for act in activities_like_j:
                                             current_solution[nodes_to_clusters[act]].remove(act)
                                             nodes_to_clusters[act] = tci_el_sc_con

                                 if not new_cluster_found:
                                     raise Exception("Error, expection raised: no empty cluster found to eliminate SHADOW CONSTRAINT conflict")

        score_CS = calculate_total_score(current_solution, weights, large_negative)[0]
        score_BS = calculate_total_score(best_solution, weights, large_negative)[0]
        unassign_act_before = calculate_total_score(best_solution, weights, large_negative)[2]

        print(f" • Value before eliminating conflicts: {readable_score(score_BS)}"
            f"\n   /!\ There are {unassign_act_before} unassigned activities")

        if score_CS > score_BS: # If score got better, make it the new best score and allow another run
            best_solution = copy.deepcopy(current_solution)
            best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)
            run_count -= 1
            print('score_CS > score_BS')

        print("~Finished eliminating all gate and shadow conflicts~")

        el_score, el_score_excl_penalties, el_no_unassigned_activities = calculate_total_score(best_solution, weights,
                                                                                               large_negative)
        print(f" • Value after eliminating conflicts: {readable_score(el_score)}"
            f"\n   /!\ There are {el_no_unassigned_activities} unassigned activities")

        # Algorithm 1
        print("----------- Restarting Alg1 -----------")
        alg1_output_solution, alg1_nodes_to_clusters, cluster_contains_gate, cluster_to_gates = (
            refine_clusters(best_solution, best_nodes_to_clusters, num_activities, num_gates, weights,
                            shadow_constraints,
                            flights_to_activities, activities_to_flights, gates_to_indices, large_negative,
                            sc_per_act_gate_pair, sc_per_gate))

        new_score, new_score_excl_penalties, new_no_unassigned_activities = calculate_total_score(alg1_output_solution, weights,
                                                                                               large_negative)
        print(f" • Value after reinjecting in Alg1: {readable_score(new_score)}"
            f"\n   /!\ There are {new_no_unassigned_activities} unassigned activities")

        # Prepare to restart Alg3
        current_solution = copy.deepcopy(alg1_output_solution)
        nodes_to_clusters = copy.deepcopy(alg1_nodes_to_clusters)


    return final_best_solution, nodes_to_clusters

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
        clusters[f"cluster_{it}"] = [gate]
        nodes_to_clusters[gate] = f"cluster_{it}"
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

    can_improve_more = True

    vertex_is_gate = {}             # keys = vertex names, values = binary indicating if vertex is a gate vertex
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

    solution_iterator = 0           # index of the currently found solution (0=initial solution)
    maximum_move_count = 50000      # large number that should never be reached
    count3 = 0
    while can_improve_more:
        count3 += 1
        print(f'I AM ALG1, I DID r MOVES AND I CAN IMPROVE. Count = {count3}')

        nontabu_vertices = list(activities_to_flights.keys())  # Only flight activities are made nontabu
        current_no_tabu_vertices = len(nontabu_vertices)        # used to check if any improving moves have been found in the current iteration

        current_solution, nodes_to_clusters, cluster_contains_gate, cluster_to_gates = solution_data_per_iterator[solution_iterator]
        target_solution = copy.deepcopy(current_solution)

        # for each vertex: find the best move that leads to a feasible neighbour
        for vertex in nontabu_vertices:
            current_cluster_id = find_my_cluster(vertex, current_solution)
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

                    # 2. if target cluster is empty: current cluster needs to contain at least 2 elements (if contains 1 -> move not allowed)
                    if len(current_solution[target_cluster_id]) == 0 and len(current_solution[current_cluster_id]) == 1:
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

    Alg1_unass_act = calculate_total_score(best_solution, weights, large_negative)[2]

    print(f"~Best reassignment solution found at {best_iterator}th iteration~")
    print(f'--- I am alg1 and I have {Alg1_unass_act} unassigned activities ---')

    return best_solution, best_nodes_to_clusters, best_cluster_contains_gate, best_cluster_to_gates

def apply_two_opt_step(solution, weights, C):
    """Applies a 2-opt algorithm to ..."""
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
                                           large_negative, sc_per_act_gate_pair, sc_per_gate):
    # Algorithm 2
    current_solution, nodes_to_clusters = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_score = calculate_total_score(current_solution, weights, large_negative)[0]
    best_score0 = best_score
    best_solution = copy.deepcopy(current_solution)     # Otherwise while loop always runs with current solution
    best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)   # Otherwise nodes_to_clusters is modified

    limite_run_count = 0
    run_count = 1
    while limite_run_count < 7:
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
            # best_solution = copy.deepcopy(current_solution)
            break  # Terminate the process if no improvement is found

        elif score_alg1 > best_score:
            best_solution = copy.deepcopy(refined_solution)
            best_nodes_to_clusters = copy.deepcopy(refined_nodes_to_clusters)
            best_score = score_alg1
            limite_run_count = 0  # Reset the limit run count if improvement is found
            run_count +=1
            # print("New best solution found, score updated:", readable_score(best_score))

        else:
            limite_run_count += 1  # Increment limit run count if no improvement
            run_count += 1

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
              f"\n   /!\ There are still {el_no_unassigned_activities} unassigned activities out of {num_activities} ({str(100*el_no_unassigned_activities/num_activities)[:4]}%)")
        print(f"   Value of current best solution: {readable_score(best_score)}\n"
              f"   Improvement/deterioration from the start by {readable_score(best_score-best_score0)} ({str((best_score-best_score0)*100/abs(best_score0))[0:7]}%)")
        print(f"================================= Add: {el_score_excl_penalties}")  #

        suboptimalGates, amountSuboptimalGates, towings, amountTowings = suboptimalGates_and_towing(refined_solution, flights_to_activities, activities_to_flights, refined_nodes_to_clusters)
        print(f"   Of the 26 remote (suboptimal) gates, {amountSuboptimalGates} have activities ({str(100*(amountSuboptimalGates)/26)[0:5]}), and {amountTowings} towings.")

    return best_solution, best_score

def iterative_refinement_gate_optimization_new(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                           shadow_constraints, num_flights,
                                           activities_to_flights, gates_to_indices, flights_to_activities,
                                           large_negative, sc_per_act_gate_pair, sc_per_gate):
    # Algorithm 2
    current_solution, nodes_to_clusters = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_score = calculate_total_score(current_solution, weights, large_negative)[0]
    best_score0 = best_score
    best_solution = copy.deepcopy(current_solution)     # Otherwise while loop always runs with current solution
    best_nodes_to_clusters = copy.deepcopy(nodes_to_clusters)   # Otherwise nodes_to_clusters is modified

    # Algorithm 1
    refined_solution, refined_nodes_to_clusters, cluster_contains_gate, cluster_to_gates = (
        refine_clusters(best_solution, best_nodes_to_clusters, num_activities, num_gates, weights, shadow_constraints,
                        flights_to_activities, activities_to_flights, gates_to_indices, large_negative,
                        sc_per_act_gate_pair, sc_per_gate))
    score_alg1, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)

    # Algorithm 3
    final_score, final_score_excl_penalties, final_no_unassigned_activities = eliminate_conflicts_new(refined_solution, M_validGate,
                        U_successor, activities_to_flights, flights_to_activities, refined_nodes_to_clusters, shadow_constraints,
                        weights, large_negative, P_preferences, num_activities, num_gates, gates_to_indices, sc_per_act_gate_pair,
                        sc_per_gate)

    print('=====================')
    print('=====================')
    print('=====================')
    print(f"FINAL SCORE IS: {final_score}, and final amount of unassigned activities is: {final_score_excl_penalties}!!!")
    print('=====================')
    print('=====================')
    print('=====================')

    return best_solution, best_score

def pre_optimized_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                         activities_to_flights, gates_to_indices, flights_to_activities):
    current_solution = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_solution = refine_clusters(current_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
    best_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(best_solution, weights, large_negative)

    limite_run_count = 0
    while limite_run_count < 7:
        # Apply a 2-opt step to refine the solution further by examining pairs of activities
        two_opt_refined_solution = apply_two_opt_step(current_solution, weights, U_successor)
        refined_solution = refine_clusters(two_opt_refined_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)

        if current_score > best_score:
            best_solution = refined_solution[:]
            best_score = current_score
            limite_run_count = 0  # Reset if an improvement is found
        else:
            limite_run_count += 1  # Continue if no improvement

        # Reassign any non-optimal gate assignments and handle conflicts
        reassign_vertices(refined_solution, weights, M_validGate, P_preferences)
        eliminate_conflicts(refined_solution, M_validGate, U_successor)

    return best_solution

def integrated_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
                                      activities_to_flights, gates_to_indices, flights_to_activities):
    current_solution = initialize_clusters(weights, activities_to_flights, gates_to_indices, U_successor)
    best_solution = apply_two_opt_step(current_solution, weights, U_successor)  # Apply 2-opt optimization here
    best_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(best_solution, weights, large_negative)

    # Further refinement loop
    limite_run_count = 0
    while limite_run_count < 7:
        refined_solution = refine_clusters(best_solution, num_activities, num_gates, weights, shadow_constraints, flights_to_activities,
                        activities_to_flights, gates_to_indices)
        current_score, score_excl_penalties, no_unassigned_activities = calculate_total_score(refined_solution, weights, large_negative)

        if current_score < best_score:
            best_solution = refined_solution[:]
            best_score = current_score
            limite_run_count = 0  # Reset the limit run count if improvement is found
        else:
            limite_run_count += 1  # Increment limit run count if no improvement

        # Reassign any non-optimal gate assignments and handle conflicts
        reassign_vertices(refined_solution, weights, M_validGate, P_preferences)
        eliminate_conflicts(refined_solution, M_validGate, U_successor)

    return best_solution

def readable_score(n):
    return f"{n:,}"



def suboptimalGates_and_towing(solution, flights_to_activities, activities_to_flights, nodes_to_clusters):
    suboptimalGates = []
    towings = []

    for cluster in solution:
        for vertex in solution[cluster]:
            if not vertex_is_act(vertex):   # vertex = gates
                gate = vertex
                if gate[0] != '1' and gate[0] != '2':   # If gate is remote
                    if len(solution[cluster]) > 1:      # If gate is not alone in the cluster
                        suboptimalGates.append(gate)
            else:   # vertex = activity
                # vertex_cluster = nodes_to_clusters[vertex]
                flight = activities_to_flights[vertex]
                flight_is_towed = False
                otherActivities = flights_to_activities[flight]
                for otherActivity in otherActivities:
                    if nodes_to_clusters[otherActivity] != cluster: # if otherActivity is not in same cluster
                        flight_is_towed = True
                if flight_is_towed:
                    towings.append(flight)

    amountSuboptimalGates = len(suboptimalGates)
    amountTowings = len(towings)

    return suboptimalGates, amountSuboptimalGates, towings, amountTowings


















