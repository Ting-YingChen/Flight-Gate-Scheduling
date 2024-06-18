from gurobipy import GRB

from Example_Input import flights, num_flights, gates, num_gates, T, P, U, M, alpha1, alpha2, alpha3, t_max, shadow_constraints
import Example_Input as ex
import CPP_MIP as cpp
# import FGS_MIP as fgs
# import Heuristic

def main():
    # Load and prepare data
    # data = dp.load_data("path_to_your_data_file")
    # processed_data = dp.preprocess_data(data)

    large_negative = ex.calculate_large_negative(num_flights, T, P, U, M, alpha1, alpha2, alpha3, t_max)
    vertices, weights = ex.get_weight_matrix(num_flights, num_gates, T, P, U, M, alpha1, alpha2, alpha3, t_max, large_negative)
    # print("large_negative:", large_negative)
    # print("weights:", weights)

    # CPP Model
    # Build the model and retrieve the solution and cluster assignments
    cpp_solution = cpp.build_cpp_model(vertices, weights, shadow_constraints)
    print(cpp_solution) # why all 0???

    # FGS MIP Model


    # Heuristic Model


    # Print or process the solutions
    # print("CCP Solution:", ccp_solution)
    # print("FGS Solution:", fgs_solution)
    # print("Heuristic Solution:", heuristic_solution)

if __name__ == "__main__":
    main()
