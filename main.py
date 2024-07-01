from instance_TYorganised import num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, shadow_constraints
import vertices_weights as vw
import CPP_MIP as cpp
# import FGS_MIP as fgs
import Heuristic

def main():
    # Load and prepare data
    # data = dp.load_data("path_to_your_data_file")
    # processed_data = dp.preprocess_data(data)

    large_negative = vw.calculate_large_negative(num_flights, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max)
    vertices, weights = vw.get_weight_matrix(num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative)
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
