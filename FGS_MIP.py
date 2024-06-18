from gurobipy import Model, GRB, quicksum

# Callback function to add lazy constraints
def mycallback(model, where):
    if where == GRB.Callback.MIPSOL:
        for (i, j) in model._shadow_constraints:
            if (i, j) in model._x and model.cbGetSolution(model._x[i, j]) > 0.5:
                model.cbLazy(model._x[i, j] == 0)


def build_FGS_model(n, m, P, U, T, M, shadow_restrictions, alpha1, alpha2, alpha3, t_max):
    model = Model("FlightGateScheduling")
    model.setParam(GRB.Param.LazyConstraints, 1)  # Enable lazy constraints

    # Decision variables for each activity being assigned to each gate
    x = model.addVars(n, m + 1, vtype=GRB.BINARY,
                      name="x")  # Number of real gates is num_gates; the last index is assumed to be the dummy gate

    # Constraints
    # Assign each activity to exactly one of its allowable gates
    for i in range(n):
        model.addConstr(quicksum(x[i, j] for j in range(m + 1) if j in M[i]) == 1, name=f"Assign_{i}")
        # '''can include dummy gate it in this quicksum (might leader to a tighter LP relaxation)'''

    # Non-overlapping constraint (1)
    for i in range(n):
        for j in range(n):
            if T[i][j] < 0:
                for k in range(m):
                    model.addConstr(x[i, k] + x[j, k] <= 1, name=f"Overlap_{i}_{j}_{k}")

    # Shadow restrictions (2)
    for (i, k, j, l) in shadow_restrictions:
        model.addConstr(x[i, k] + x[j, l] <= 1, name=f"Shadow_{i}_{j}")

    # Objective components (3)

    # Append significantly negative scores for the dummy gate
    P_star = [prefs + [-1000] for prefs in P]  # Add a very undesirable score for the dummy gate

    # z1: Minimize the negative sum of adjusted preferences
    z1 = - quicksum(P_star[i][j] * x[i, j] for i in range(n) for j in range(m + 1))
    # ''' - quicksum(P_star[i][j] * x[i, j] for (i,j) in x). negative is important!'''

    # Define a new decision variable for tows between activities and their successors
    '''Good practice: first define ALL variables, then define ALL constraints, and ultimately define the objective function
    '''
    tows = model.addVars(n, m + 1, vtype=GRB.BINARY, name="tows")
    # '''Towing to the dummy gate also needs to be possible (-> tighter lower bounds)'''

    # Calculate tows:
    for i in range(n):
        '''Each activity must have a successor, i.e. U[i] \in N for all i
        In the trivial case that would be the activity itself (->U[i] = i)'''
        for k in range(m + 1):
            if U[i] != i:  # Check for a valid successor

                # If activity i is assigned to gate k and its successor U[i] to a different gate
                model.addConstr(tows[i, k] >= x[i, k] - x[U[i], k], name=f"TowIfDifferent_{i}_{k}")

                # model.addConstr(tows[i, k] >= x[i, k] - x[U[i], k], name=f"TowIfDifferent1_{i}_{k}")
                # model.addConstr(tows[i, k] >= x[U[i], k] - x[i, k], name=f"TowIfDifferent2_{i}_{k}")
                '''If I understand it correctly, it should be that tows[i,k] = 1 <=> flight associated with activity i
                needs to be towed away from gate k after activity i is done.
                First constraint: "if activity i is assigned to gate k, but its successor is not, we need to tow the plane 
                away from k after finishing i"
                second constraint: "if activity i is NOT assigned to gate k, but its success is, we need to tow the plane
                towards k after finishing i"
                The latter constraint set would then lead to every tow being counted twice if I'm not mistaken
                '''

    # Redefine z2 using the new tow variables
    z2 = quicksum(tows[i, k] for i in range(n) for k in range(m))

    # z3: Buffer time deficit
    # z3 = quicksum(max(t_max - T[i][j], 0) * x[i, k] * x[j, k] for i in range(n) for j in range(i +1, n) for k in range(m))
    '''This is a quadratic constraint. It can be linearized by introducing variables buffer[i,j] for activities i and j,
    bounding them from above by x[i,k]*(max(t_max - T_[i][j],0)) and x[j,k]*(max(t_max - T_[i][j],0)).
    '''

    buffer = model.addVars(n, n, vtype=GRB.BINARY, name="buffer")
    # TODO: Implement new buffer time constraint here

    # Combined objective
    model.setObjective(alpha1 * z1 + alpha2 * z2 + alpha3 * z3, GRB.MINIMIZE)
    model.optimize()

    return model, x, tows