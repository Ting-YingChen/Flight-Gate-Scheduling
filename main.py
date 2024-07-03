import Instance
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

    # load excel file and create all relevant data structures
    LOCAL_PATH = '/Users/chentingying/Documents/tum/AS_Operation_Management/Brussels.xlsm'
    check_output = False
    # Import data
    flightsBrussels, gatesBrussels, T_timeDiff, Gates_N, Gates_D, num_flights, num_gates, Flight_No, Gate_No, ETA, ETD, P_preferences, \
        flights_to_activities, activities_to_flights, U_successor, M_validGate, shadow_constraints, no_towable_flights,\
        gates_to_indices, indices_to_gates = Instance.createInputData(LOCAL_PATH, check_output)

    large_negative = vw.calculate_large_negative(Flight_No, num_flights, no_towable_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
    weights = vw.get_weight_matrix(Flight_No, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative,
                                             flights_to_activities, activities_to_flights, gates_to_indices, indices_to_gates)
    # Note: the keys of the dictionary 'weights' are exactly the names of all vertices present in the graph!

    print("large_negative:", large_negative)
    print("weights:", weights)

    # CPP Model
    # Build the model and retrieve the solution and cluster assignments
    cpp_solution = cpp.build_cpp_model(weights, shadow_constraints)
    print(cpp_solution)

    # FGS MIP Model


    # Heuristic Model
    # todo: adjust it so it works without 'vertices' list
    heuristic_solution = Heuristic.iterative_gate_optimization(weights, U_successor, M_validGate, P_preferences)
    # print("Heuristic Solution:", heuristic_solution)

if __name__ == "__main__":
    main()
