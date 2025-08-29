"""optimizer.py
Resource allocation optimizer.

Assign patients to partners given capacities.
Uses OR-Tools CP-SAT solver.

Patients should be provided as a list of dicts with:
- patient_id
- priority_level (Emergency/High/Medium/Low)
- demand_icu (0/1)
- demand_general (0/1)
- nurse_need (integer, default 1)

Partners should be provided as a list of dicts with:
- partner_id
- icu_beds
- general_beds
- nurses

Objective: maximize sum(weight * assigned) where weight depends on priority level.
"""
from ortools.sat.python import cp_model

PRIORITY_WEIGHT = {
    'Emergency': 100,
    'High': 50,
    'Medium': 20,
    'Low': 5
}

def optimize_allocation(patients, partners):
    model = cp_model.CpModel()
    # decision variables: x[p_idx][q_idx] = 1 if patient p assigned to partner q
    x = {}
    for p_idx, p in enumerate(patients):
        for q_idx, q in enumerate(partners):
            x[(p_idx,q_idx)] = model.NewBoolVar(f"x_p{p_idx}_q{q_idx}")

    # each patient can be assigned to at most one partner
    for p_idx, p in enumerate(patients):
        model.Add(sum(x[(p_idx,q_idx)] for q_idx in range(len(partners))) <= 1)

    # capacity constraints
    # ICU beds
    for q_idx, q in enumerate(partners):
        model.Add(sum(x[(p_idx,q_idx)] * int(p.get('demand_icu',0)) for p_idx,p in enumerate(patients)) <= int(q.get('icu_beds',0)))
        model.Add(sum(x[(p_idx,q_idx)] * int(p.get('demand_general',0)) for p_idx,p in enumerate(patients)) <= int(q.get('general_beds',0)))
        model.Add(sum(x[(p_idx,q_idx)] * int(p.get('nurse_need',1)) for p_idx,p in enumerate(patients)) <= int(q.get('nurses',0)))

    # Objective: maximize weighted assignments
    objective_terms = []
    for p_idx, p in enumerate(patients):
        w = PRIORITY_WEIGHT.get(p.get('priority_level','Low'), 5)
        for q_idx, q in enumerate(partners):
            objective_terms.append(x[(p_idx,q_idx)] * w)
    model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)

    assignments = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for p_idx, p in enumerate(patients):
            for q_idx, q in enumerate(partners):
                if solver.Value(x[(p_idx,q_idx)]) == 1:
                    assignments.append({
                        'patient_id': p['patient_id'],
                        'patient_name': p.get('name'),
                        'assigned_partner_id': q.get('partner_id'),
                        'assigned_partner_name': q.get('partner_name'),
                        'priority_level': p.get('priority_level')
                    })
    return assignments