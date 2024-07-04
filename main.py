import Instance
import vertices_weights as vw
import CPP_MIP as cpp
# import FGS_MIP as fgs
import Heuristic

# Configurations for data import
LOCAL_PATH_TingYing = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'
LOCAL_PATH_Arthur = '/Users/arthurdebelle/Desktop/TUM/SoSe 2024/Ad.S - OM/Project/CODING/Airports data/Brussels (EBBR)/Brussels.xlsm'
LOCAL_PATH_Andreas = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels copy.xlsm'
LOCAL_PATH = LOCAL_PATH_Arthur

def main(local_path):
    # 0. define all relevant model parameters
    # Parameters based on experiences
    alpha1 = 1  # Preference scaling factor
    alpha2 = 20  # Reward for avoiding tows
    alpha3 = 100  # Penalty scaling factor for buffer time deficits
    t_max = 30

    check_output = False

    # Import data
    (flights, num_flights, gates, num_gates, T_timeDiff, Gates_N,
    Flight_No, ETA, ETD, RTA, RTD, AC_size, Gate_No, Max_Wingspan, Is_Int, Is_LowCost, Is_Close,
    P_preferences,
    flights_to_activities, activities_to_flights, U_successor, no_towable_flights,
    M_validGate,
    shadow_constraints,
    gates_to_indices, indices_to_gates) = Instance.createInputData(local_path, check_output)


    # Load and prepare data
    # data = dp.load_data("path_to_your_data_file")
    # processed_data = dp.preprocess_data(data)

    large_negative = vw.calculate_large_negative(Flight_No, num_flights, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
    weights = vw.get_weight_matrix(Flight_No, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative,
                                             flights_to_activities, activities_to_flights, gates_to_indices, indices_to_gates)
    # Note: the keys of the dictionary 'weights' are exactly the names of all vertices present in the graph!

    print("large_negative:", large_negative)
    # print("weights:", weights)

    # CPP Model
    # Build the model and retrieve the solution and cluster assignments
    cpp_solution = cpp.build_cpp_model(weights, shadow_constraints)
    # print(cpp_solution) # why all 0???

    # FGS MIP Model


    # Heuristic Model
    # todo: adjust it so it works without 'vertices' list
    heuristic_solution = Heuristic.iterative_gate_optimization(weights, U_successor, M_validGate, P_preferences)

    # Print or process the solutions
    # print("CCP Solution:", ccp_solution)
    # print("FGS Solution:", fgs_solution)
    print("Heuristic Solution:", heuristic_solution)

if __name__ == "__main__":
    main(LOCAL_PATH)
