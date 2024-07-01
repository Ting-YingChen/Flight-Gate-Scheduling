import instance_TYorganised
import vertices_weights as vw
import CPP_MIP as cpp
# import FGS_MIP as fgs
import Heuristic

def main():
    # 0. define all relevant model parameters
    # Parameters based on experiences
    alpha1 = 1  # Preference scaling factor
    alpha2 = 20  # Reward for avoiding tows
    alpha3 = 100  # Penalty scaling factor for buffer time deficits
    t_max = 30


    #jsdvbjs
    # load excel file and create all relevant data structures
    LOCAL_PATH = 'C:/Users/ge92qac/PycharmProjects/Flight-Gate-Scheduling/Brussels copy.xlsm'
    check_output = False
    # Import data
    flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates, Flight_No, Gate_No, ETA, ETD, P_preferences, \
        flights_to_activities, activities_to_flights, U_successor, M_validGate, shadow_constraints, no_towable_flights = instance_TYorganised.createInputData(LOCAL_PATH, check_output)


    # Load and prepare data
    # data = dp.load_data("path_to_your_data_file")
    # processed_data = dp.preprocess_data(data)

    large_negative = vw.calculate_large_negative(Flight_No, num_flights, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
    vertices, weights = vw.get_weight_matrix(Flight_No, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative,
                                             flights_to_activities, activities_to_flights)
    print("large_negative:", large_negative)
    # print("weights:", weights)

    # CPP Model
    # Build the model and retrieve the solution and cluster assignments
    cpp_solution = cpp.build_cpp_model(vertices, weights, shadow_constraints)
    # print(cpp_solution) # why all 0???

    # FGS MIP Model


    # Heuristic Model
    heuristic_solution = Heuristic.iterative_gate_optimization(vertices, weights, U_successor, M_validGate, P_preferences)

    # Print or process the solutions
    # print("CCP Solution:", ccp_solution)
    # print("FGS Solution:", fgs_solution)
    print("Heuristic Solution:", heuristic_solution)

if __name__ == "__main__":
    main()
