from gurobipy import Model, GRB, quicksum

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


def build_cpp_model(weights, shadow_constraints):
    print("Solving with CCP: ")

    # Initialize the model
    model = Model("GateAssignmentCPP")
    model.setParam(GRB.Param.LazyConstraints, 1)  # Enable lazy constraints
    #model.setParam('OutputFlag', 0)

    # Decision variables: x[i, j] = 1 if i and j are in the same clique, 0 otherwise

    no_nodes = len(weights)
    x = {}
    for node_i in weights:
        for node_j in weights:
            if (node_j, node_i) not in x:
                x[(node_i, node_j)] = model.addVar(vtype=GRB.BINARY, name=f"x[{node_i},{node_j}]")

    # Objective: Maximize the sum of the weights for edges within the same clique
    model.setObjective(quicksum([weights[i][j] * x[i, j] for (i,j) in x]), GRB.MAXIMIZE)

    # Transitivity constraints to ensure that the solution forms a valid clique (4)
    for i in range(no_nodes):
        node_i = list(weights.keys())[i]
        for j in range(i + 1, no_nodes):
            node_j = list(weights.keys())[j]
            for k in range(j + 1, no_nodes):
                node_k = list(weights.keys())[k]
                model.addConstr(x[(node_i, node_j)] + x[(node_j, node_k)] - x[(node_i, node_k)] <= 1)
                model.addConstr(x[(node_i, node_j)] - x[(node_j, node_k)] + x[(node_i, node_k)] <= 1)
                model.addConstr(-x[(node_i, node_j)] + x[(node_j, node_k)] + x[(node_i, node_k)] <= 1)

    # Store variables and constraints for the callback
    model._x = x
    model._shadow_constraints = shadow_constraints
    model.optimize(callback_shadow_constraints)  # Optimize with the callback function to add lazy constraints

    # Process results
    if model.status == GRB.Status.OPTIMAL:
        print("Optimal solution found with total score:", model.objVal)
        solution = {f"x[{i},{j}]": x[i, j].X for (i,j) in x if
                    x[i, j].X > 0.5}
        print("Solution edges:", solution)
    else:
        print("No optimal solution found. Status:", model.status)

    return model