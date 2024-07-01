from gurobipy import Model, GRB, quicksum
import vertices_weights as vw
from vertices_weights import num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, shadow_constraints

# Callback function to add lazy constraints
'''
Denote by (x_ij)^* the set of all binary variables x_ij that are set to 1 in your current optimal solution.
You can then cut off this solution by adding the constraint sum_((i,j): x_ij^* = 1) x_ij <= |(x_ij)^*| - 1,
where the latter expression is the number of nonzero variables in your current optimal solution.
'''


def callback_shadow_constraints(model, where):
    """
    Callback function to add lazy constraints for shadow constraints during the optimization.
    Triggered during the MIPSOL phase where a feasible integer solution is found.

    Parameters:
        model: The Gurobi model object.
        where: Condition indicating the phase of the optimization process.
    """
    if where == GRB.Callback.MIPSOL:
        violated_constraints = 0
        # Access the shadow constraints and decision variables from model object

        for (i, k, j, l) in model._shadow_constraints:
            # Ensure both sets of keys exist in the model dictionary to avoid key errors
            if (i, k) in model._x and (j, l) in model._x:
                # Retrieve the solution values directly to minimize callback overhead
                x_ik = model.cbGetSolution(model._x[i, k])
                x_jl = model.cbGetSolution(model._x[j, l])
                # Check if both variables are set to 1 (or rounded to 1), indicating a violation
                if x_ik > 0.5 and x_jl > 0.5:
                    # Add a lazy constraint to enforce that these two activities cannot overlap
                    model.cbLazy(model._x[i, k] + model._x[j, l] <= 1)
                    violated_constraints += 1
                    print(f"Lazy constraint added to prevent simultaneous scheduling of {i} at {k} and {j} at {l}")

        if violated_constraints > 0:
            print(f"{violated_constraints} constraints were violated and addressed.")


def build_cpp_model(vertices, weights, shadow_constraints):
    large_negative = vw.calculate_large_negative(num_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2,
                                              alpha3, t_max)
    vertices, weights = vw.get_weight_dict(num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate,
                                        alpha1, alpha2, alpha3, t_max, large_negative)
    print("\nSolving with CCP: ")

    # Initialize the model
    model = Model("GateAssignmentCPP")
    model.setParam(GRB.Param.LazyConstraints, 1)  # Enable lazy constraints
    model.setParam('OutputFlag', 0)

    # Decision variables: x[i, j] = 1 if i and j are in the same clique, 0 otherwise
    # Decision variables using dictionary comprehension
    x = {(i, j): model.addVar(vtype=GRB.BINARY, name=f"x[{i},{j}]") for i in range(vertices) for j in
            range(i + 1, vertices)}

    # Objective: Maximize the sum of the weights for edges within the same clique
    model.setObjective(quicksum(weights.get((i, j), 0) * x[i, j] for i in range(vertices) for j in range(i + 1, vertices)), GRB.MINIMIZE)

    # Transitivity constraints to ensure that the solution forms a valid clique (4)
    # Transitivity constraints using dictionary keys directly
    for i in range(vertices):
        for j in range(i + 1, vertices):
            for k in range(j + 1, vertices):
                model.addConstr(x[(i, j)] + x[(j, k)] - x[(i, k)] <= 1)
                model.addConstr(x[(i, j)] - x[(j, k)] + x[(i, k)] <= 1)
                model.addConstr(-x[(i, j)] + x[(j, k)] + x[(i, k)] <= 1)

    # Store variables and constraints for the callback
    model._x = x
    model._shadow_constraints = shadow_constraints
    model.optimize(callback_shadow_constraints)  # Optimize with the callback function to add lazy constraints

    # Process results and print solution
    if model.status == GRB.Status.OPTIMAL:
        print("Optimal solution found with total score:", model.objVal)
        flight_assignments = {i: None for i in range(num_flights)}
        for (i, j), var in x.items():
            if var.X > 0.5:
                if i < num_flights and j >= num_flights:
                    gate_index = j - num_flights
                    flight_assignments[i] = gate_index
                elif j < num_flights and i >= num_flights:
                    gate_index = i - num_flights
                    flight_assignments[j] = gate_index
        for flight, gate in flight_assignments.items():
            if gate is not None:
                print(f"Flight {flight} is assigned to gate {gate}")
            else:
                print(f"Flight {flight} is not assigned to any gate.")
        return {key: value.X for key, value in x.items() if value.X > 0.5}
    else:
        print("No optimal solution found. Status:", model.status)

    return model

# Calculate large_negative value and weights
large_negative = vw.calculate_large_negative(num_flights, T_timeDiff, P_preferences, M_validGate, alpha1, alpha2, alpha3, t_max)
vertices, weights = vw.get_weight_dict(num_flights, num_gates, T_timeDiff, P_preferences, U_successor, M_validGate, alpha1, alpha2, alpha3, t_max, large_negative)

# Now call the build_cpp_model function
result = build_cpp_model(vertices, weights, shadow_constraints)
print(result)










