import gurobipy as gp
from gurobipy import Model, GRB, quicksum


# Callback function to add lazy constraints
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

def build_FGS_model(num_flights, num_gates, P_preferences, U_successor, T_timeDiff, M_validGate, shadow_constraints, alpha1, alpha2, alpha3, t_max):
    model = Model("FlightGateScheduling")
    model.setParam(GRB.Param.LazyConstraints, 1)  # Enable lazy constraints

    # Decision variables for each activity being assigned to each gate
    x = model.addVars(num_flights, num_gates + 1, vtype=GRB.BINARY,name="x")  # Number of real gates is num_gates; the last index is assumed to be the dummy gate
    tows = model.addVars(num_flights, num_gates + 1, vtype=GRB.BINARY, name="tows")
    buffer = model.addVars(num_flights, num_flights, num_gates, vtype=GRB.BINARY, name="buffer")

    # Append significantly negative scores for the dummy gate
    P_star = {i: prefs + [-1000] for i, prefs in P_preferences.items()}

    # Constraints
    # Assign each activity to exactly one of its allowable gates
    for i in range(num_flights):
        model.addConstr(quicksum(x[i, j] for j in range(num_gates + 1) if j in M_validGate[i]) == 1, name=f"Assign_{i}")
        # '''can include dummy gate it in this quicksum (might leader to a tighter LP relaxation)'''

    # Non-overlapping constraint (1)
    for i in range(num_flights):
        for j in range(num_flights):
            if T_timeDiff[(i, j)] < 0:
                for k in range(num_gates):
                    model.addConstr(x[i, k] + x[j, k] <= 1, name=f"Overlap_{i}_{j}_{k}")

    # Towing constraints
    for i in range(num_flights):
        '''Each activity must have a successor, i.e. U[i] \in N for all i
        In the trivial case that would be the activity itself (->U[i] = i)'''
        for k in range(num_gates + 1):
            if U_successor[i] != i:  # Ensuring the successor is valid and different
                # Tow is needed if flight i is at gate k and its successor is not at gate k.
                model.addConstr(tows[i, k] >= x[i, k] - x[U_successor[i], k], name=f"TowIfDifferent_{i}_{k}")
                # This ensures a tow is planned if the plane needs to move after activity i.

                # Removing the second condition to avoid double-counting:
                # model.addConstr(tows[i, k] >= x[U_successor[i], k] - x[i, k], name=f"TowIfDifferent2_{i}_{k}")
                # This line would have checked if the successor activity is at gate k while i is not, which is unnecessary

                '''If I understand it correctly, it should be that tows[i,k] = 1 <=> flight associated with activity i
                needs to be towed away from gate k after activity i is done.
                First constraint: "if activity i is assigned to gate k, but its successor is not, we need to tow the plane 
                away from k after finishing i"
                second constraint: "if activity i is NOT assigned to gate k, but its success is, we need to tow the plane
                towards k after finishing i"
                The latter constraint set would then lead to every tow being counted twice if I'm not mistaken
                '''

    # Buffer constraint
    for i in range(num_flights):
        for j in range(i + 1, num_flights):
            for k in range(num_gates):
                # Constraint to ensure buffer is zero when not both flights are at the same gate
                max_buffer_time = max(t_max - T_timeDiff[(i, j)], 0)
                # Constraint to activate buffer if both flights are at the same gate and the buffer condition is not met
                model.addConstr(buffer[i, j, k] >= x[i, k] + x[j, k] - 1, name=f"Buffer_Activation_{i}_{j}_{k}")
                model.addConstr(buffer[i, j, k] <= x[i, k], name=f"Buffer_UpperBound1_{i}_{j}_{k}")
                model.addConstr(buffer[i, j, k] <= x[j, k], name=f"Buffer_UpperBound2_{i}_{j}_{k}")

    # Shadow restrictions (2)
    for (i, k, j, l) in shadow_constraints:
        model.addConstr(x[i, k] + x[j, l] <= 1)

    # Objective components (3)
    # z1: Minimize the negative sum of adjusted preferences
    z1 = - quicksum(P_star[i][j] * x[i, j] for i in range(num_flights) for j in range(num_gates + 1))

    # Redefine z2 using the new tow variables
    z2 = quicksum(tows[i, k] for i in range(num_flights) for k in range(num_gates + 1))

    # z3: Buffer time deficit
    z3 = quicksum(max(t_max - T_timeDiff[(i, j)], 0) * buffer[i, j, k] for i in range(num_flights) for j in range(i + 1, num_flights) for k in range(num_gates))
    '''This is a quadratic constraint. It can be linearized by introducing variables buffer[i,j] for activities i and j,
    bounding them from above by x[i,k]*(max(t_max - T_[i][j],0)) and x[j,k]*(max(t_max - T_[i][j],0)).
    '''

    # Combined objective
    model.setObjective(alpha1 * z1 + alpha2 * z2 + alpha3 * z3, GRB.MINIMIZE)
    model.optimize()

    return model, x, tows

# Dictionary-based data
num_flights = 4
num_gates = 3
P_preferences = {0: [10, 20, 30], 1: [20, 30, 10], 2: [30, 10, 20], 3: [10, 30, 20]}
U_successor = {0: 1, 1: 2, 2: 3, 3: 0}
T_timeDiff = {
    (0, 0): 0, (0, 1): 2, (0, 2): -1, (0, 3): -1,
    (1, 0): -1, (1, 1): 0, (1, 2): 3, (1, 3): -1,
    (2, 0): -1, (2, 1): -1, (2, 2): 0, (2, 3): 4,
    (3, 0): 1, (3, 1): -1, (3, 2): -1, (3, 3): 0
}
M_validGate = {0: {0, 1, 3}, 1: {1, 2, 3}, 2: {0, 2, 3}, 3: {1, 3}}

# Other parameters remain unchanged
shadow_constraints = [
    (0, 0, 1, 0),  # Flight 0 and Flight 1 cannot both use Gate 0.
    (1, 2, 2, 2),  # Flight 1 and Flight 2 cannot both use Gate 2.
    (2, 1, 3, 1)   # Flight 2 and Flight 3 cannot both use Gate 1.
]
t_max = 5
alpha1, alpha2, alpha3 = 1, 0.5, 0.2

# Test the model
model, x, tows = build_FGS_model(num_flights, num_gates, P_preferences, U_successor, T_timeDiff, M_validGate, shadow_constraints, alpha1, alpha2, alpha3, t_max)

# Print solution
if model.status == GRB.OPTIMAL:
    assignment = model.getAttr('X', x)
    for f in range(num_flights):
        for g in range(num_gates + 1):
            if assignment[f, g] > 0.5:
                print(f"Flight {f} is assigned to gate {g}")
else:
    print("No optimal solution found.")


