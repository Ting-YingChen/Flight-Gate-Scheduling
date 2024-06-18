from gurobipy import Model, GRB, quicksum

# Callback function to add lazy constraints
'''
Denote by (x_ij)^* the set of all binary variables x_ij that are set to 1 in your current optimal solution.
You can then cut off this solution by adding the constraint sum_((i,j): x_ij^* = 1) x_ij <= |(x_ij)^*| - 1,
where the latter expression is the number of nonzero variables in your current optimal solution.
'''
def add_lazy_shadow_constraints(model, where):
    # checks if the callback is being called during the MIPSOL phase,
    # which is when a feasible integer solution is found.
    if where == GRB.Callback.MIPSOL:
        violated_constraints = 0
        for (i, k, j, l) in model._shadow_constraints:
            if (i, k) in model._x and (j, l) in model._x:
                # effectively checking if the values of the binary variables are set to 1, since they are binary
                if model.cbGetSolution(model._x[i, k]) > 0.5 and model.cbGetSolution(model._x[j, l]) > 0.5:
                    model.cbLazy(model._x[i, k] + model._x[j, l] <= 1)
                    violated_constraints += 1


def build_cpp_model(vertices, weights, shadow_constraints):
    print("Solving with CCP: ")

    # Define the Gurobi model and set parameters
    model = Model("GateAssignmentCPP")
    model.setParam(GRB.Param.LazyConstraints, 1)  # Enable lazy constraints
    model.setParam('OutputFlag', 0)

    # Decision variables: x[i, j] = 1 if i and j are in the same clique, 0 otherwise
    x = {}
    for i in range(vertices):
        for j in range(i + 1, vertices):
            x[i, j] = model.addVar(vtype=GRB.BINARY, name=f"x[{i},{j}]")

    print(weights)
    print(vertices)
    # Objective: Maximize the sum of the weights for edges within the same clique
    model.setObjective(quicksum(weights[i][j] * x[i, j] for i in range(vertices) for j in range(i + 1, vertices)), GRB.MINIMIZE)

    # Add transitivity constraints for forming valid cliques (4)
    for i in range(vertices):
        for j in range(vertices):
            for k in range(vertices):
                if i < j < k:
                    model.addConstr(x[i, j] + x[j, k] - x[i, k] <= 1)
                    model.addConstr(x[i, j] - x[j, k] + x[i, k] <= 1)
                    model.addConstr(-x[i, j] + x[j, k] + x[i, k] <= 1)

    # Store variables and constraints for the callback
    model._x = x
    model._shadow_constraints = shadow_constraints
    model.optimize(add_lazy_shadow_constraints)  # Optimize with the callback function to add lazy constraints

    # Prepare cluster assignments from the solution
    if model.status == GRB.Status.OPTIMAL:
        print("Optimal solution found with total score:", model.objVal)
        cliques = {}
        solution = model.getAttr('x', x)
        for (i, j), value in solution.items():
            if value > 0.5:
                cliques.setdefault(i, []).append(j)
                cliques.setdefault(j, []).append(i)

        # Automatically assign clusters from cliques
        C = [None] * vertices
        cluster_id = 0
        for key, value in cliques.items():
            if C[key] is None:
                # Find the lowest available cluster ID
                existing_clusters = set(C[v] for v in value if C[v] is not None)
                new_cluster_id = 0
                while new_cluster_id in existing_clusters:
                    new_cluster_id += 1
                # Assign this new cluster ID to all connected nodes
                for v in value:
                    if C[v] is None:
                        C[v] = new_cluster_id
                C[key] = new_cluster_id
                cluster_id = max(cluster_id, new_cluster_id + 1)

        print("Cluster Assignments:", C)

    else:
        print("No optimal solution found. Status:", model.status)

    return model






