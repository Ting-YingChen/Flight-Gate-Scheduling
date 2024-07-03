import time

import Instance
import instance_TYorganised
import vertices_weights as vw
import CPP_MIP as cpp
import FGS_MIP as fgs
import Heuristic

def main():
    # 0. define all relevant model parameters
    # Parameters based on experiences
    alpha1 = 1  # Preference scaling factor
    alpha2 = 20  # Reward for avoiding tows
    alpha3 = 100  # Penalty scaling factor for buffer time deficits
    t_max = 30

    # load excel file and create all relevant data structures
    LOCAL_PATH_TingYing = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'
    LOCAL_PATH_Arthur = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'
    LOCAL_PATH_Andreas = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels copy.xlsm'

    LOCAL_PATH = LOCAL_PATH_TingYing
    check_output = False

    # Import data
    flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates, Flight_No, Gate_No, ETA, ETD, P_preferences, \
        flights_to_activities, activities_to_flights, num_activities, U_successor, M_validGate, shadow_constraints, no_towable_flights,\
        gates_to_indices, indices_to_gates = Instance.createInputData(LOCAL_PATH, check_output)

    large_negative = vw.calculate_large_negative(Flight_No, num_flights, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
    weights = vw.get_weight_matrix(Flight_No, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative,
                                             flights_to_activities, activities_to_flights, gates_to_indices, indices_to_gates)
    # Note: the keys of the dictionary 'weights' are exactly the names of all vertices present in the graph!
    print("large_negative:", large_negative)
    print("weights:", weights)

    # Initialize performance records
    performance_records = {}

    # FGS MIP Model

    # CPP Model
    start_time = time.time()
    cpp_solution = cpp.build_cpp_model(weights, shadow_constraints)
    cpp_duration = time.time() - start_time
    performance_records['CPP'] = {'duration': cpp_duration, 'solution': cpp_solution}

    # Heuristic Model
    # todo: adjust it so it works without 'vertices' list

    # Iterative Refinement Heuristic Model
    start_time = time.time()
    iterative_refinement_solution = Heuristic.iterative_refinement_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences)
    iterative_refinement_duration = time.time() - start_time
    performance_records['Iterative Refinement Heuristic'] = {'duration': iterative_refinement_duration,
                                                             'solution': iterative_refinement_solution}

    # 2-opt Integrated Heuristic Model
    start_time = time.time()
    integrated_solution = Heuristic.integrated_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences)
    integrated_duration = time.time() - start_time
    performance_records['Integrated 2-opt Heuristic'] = {'duration': integrated_duration,
                                                         'solution': integrated_solution}

    # Pre-optimized 2-opt Gate Assignment Model
    start_time = time.time()
    pre_optimized_solution = Heuristic.pre_optimized_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences)
    pre_optimized_duration = time.time() - start_time
    performance_records['Pre-optimized 2-opt'] = {'duration': pre_optimized_duration,
                                                  'solution': pre_optimized_solution}

    # Print or log the performance
    for model, record in performance_records.items():
        print(f"{model} took {record['duration']} seconds and produced solution {record['solution']}")


if __name__ == "__main__":
    main()
