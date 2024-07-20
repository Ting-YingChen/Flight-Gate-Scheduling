import time
import Instance
import vertices_weights as vw
import CPP_MIP as cpp
import FGS_MIP as fgs
import Heuristic

def main(local_path, EstimatedOrReal):
    # 0. define all relevant model parameters
    # Parameters based on experiences
    alpha1 = 1  # Preference scaling factor
    alpha2 = 3  # Reward for avoiding tows
    alpha3 = 100  # Penalty scaling factor for buffer time deficits
    t_max = 30
#
    # Import data
    (flights, num_flights, gates, num_gates, T_timeDiff, Gates_N,
     Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close,
     P_preferences,
     flights_to_activities, activities_to_flights, U_successor, no_towable_flights, num_activities,
     M_validGate,
     shadow_constraints,
     gates_to_indices, indices_to_gates) = Instance.createInputData(local_path, False, EstimatedOrReal)

    large_negative = vw.calculate_large_negative(activities_to_flights, num_activities, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
    # large_negative = -20000
    weights = vw.get_weight_matrix(num_activities, activities_to_flights, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3,
                      t_max, large_negative, gates_to_indices, indices_to_gates)

    # Note: the keys of the dictionary 'weights' are exactly the names of all vertices present in the graph!
    print("large_negative:", large_negative)
    # print("weights:", weights)

    # Initialize performance records
    performance_records = {}

    # FGS MIP Model

    # CPP Model
    start_time = time.time()
    cpp_solution = cpp.build_cpp_model(weights, shadow_constraints)
    cpp_duration = time.time() - start_time
    performance_records['CPP'] = {'duration': cpp_duration, 'solution': cpp_solution}

    # Heuristic Model

    # Iterative Refinement Heuristic Model
    # sc_per_act_gate_pair, sc_per_gate = Instance.convert_sc_to_dicts(shadow_constraints)
    #
    # start_time = time.time()
    # print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~\nStarting standard heuristic\n~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    # iterative_refinement_solution, iterative_refinement_score = (
    #     Heuristic.iterative_refinement_gate_optimization_new(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences,
    #                                                      shadow_constraints, num_flights,
    #                                                      activities_to_flights, gates_to_indices, flights_to_activities,
    #                                                      large_negative,
    #                                                      sc_per_act_gate_pair, sc_per_gate))
    # iterative_refinement_duration = time.time() - start_time
    # performance_records['Iterative Refinement Heuristic'] = {'duration': iterative_refinement_duration,
    #                                                          'solution': iterative_refinement_solution}
    # print(f"Done. Runtime = {time.time() - start_time} seconds.")

    # # 2-opt Integrated Heuristic Model
    # start_time = time.time()
    # integrated_solution = Heuristic.integrated_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences, activities_to_flights, gates_to_indices)
    # integrated_duration = time.time() - start_time
    # performance_records['Integrated 2-opt Heuristic'] = {'duration': integrated_duration,
    #                                                      'solution': integrated_solution}
    #
    # # Pre-optimized 2-opt Gate Assignment Model
    # start_time = time.time()
    # pre_optimized_solution = Heuristic.pre_optimized_2opt_gate_optimization(num_activities, num_gates, weights, U_successor, M_validGate, P_preferences, activities_to_flights, gates_to_indices)
    # pre_optimized_duration = time.time() - start_time
    # performance_records['Pre-optimized 2-opt'] = {'duration': pre_optimized_duration, 'solution': pre_optimized_solution}

    # Print or log the performance
    # for model, record in performance_records.items():
    #     print(f"{model} took {record['duration']} seconds and produced solution {record['solution']}")

# Configurations for data import
LOCAL_PATH_TingYing = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'
LOCAL_PATH_Arthur = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'
LOCAL_PATH_Arthur_light = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels (less flights).xlsm'
LOCAL_PATH_Andreas = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels.xlsm'
LOCAL_PATH = LOCAL_PATH_Arthur_light

if __name__ == "__main__":
    EstimatedOrReal = "Estimated"
    # EstimatedOrReal = "Real"
    main(LOCAL_PATH, EstimatedOrReal)




