from datetime import date
from solver import Solver, save_csv, response_build
from pulp import LpStatus

def main():

    ob_weight = (50, 33, 10, 10)
    
    weekend_pattern_const = True
    from_date = date(2024, 10, 7)
    to_date = date(2024, 11, 3)
    employees = ['Raffaele', 'Roberta', 'Giacomo', 'Nunzia', 'Pouya', 'Viviana', 'Farmacista7']
    employees_far = ['Giacomo', 'Nunzia', 'Pouya']

    max_h_employee_for_day = 8
    min_h_employee_for_day = 5
    max_h_employee_for_week = 37
    min_h_employee_for_week = 35
    max_n_split_employee_for_week = 5

    solver = Solver(from_date, to_date, employees, employees_far, max_h_employee_for_day, min_h_employee_for_day, max_n_split_employee_for_week, max_h_employee_for_week, min_h_employee_for_week, ob_weight, weekend_pattern_const)
    
    '''
    solver.add_c_employee_day_leave('Bianca', 9)
    solver.add_c_employee_day_leave('Bianca', 10)
    solver.add_c_employee_day_leave('Pouya', 17)
    solver.add_c_employee_day_leave('Pouya', 18)
    solver.add_c_employee_day_leave('Viviana', 9)

    #Viviana non fa i turni 12-20
    for i in range(1,29):
        solver.add_c_employee_shiftDay_leave('Viviana', i,'A',0)
        solver.add_c_employee_shiftDay_leave('Viviana', i,'A',1)
        solver.add_c_employee_shiftDay_leave('Viviana', i,'A',2)

    # Nunzia non lavora tutti i giovedi di febbraio
    for i in [1, 8, 15, 22, 29]:
        solver.add_c_employee_day_leave('Nunzia',i)
    '''
    #status = solver.solve_PULP(timeLimit=200, gapRel = 0.05, threads=16)
    status = solver.solve_HiGHS(timeLimit=60, gapRel = 0.05, threads=16)

    #status = solver.solve_GUROBI(timeLimit=60, gapRel = 0.05, threads=16)
    #status = solver.solve_SCIP(timeLimit=120, gapRel = 0.05, threads=16)
    #status = solver.solve_GLPK(timeLimit=120)


    print('status', LpStatus[status])

    save_csv(solver, 'calendar.csv')
    print(response_build(solver))

if __name__ == '__main__':
    main()