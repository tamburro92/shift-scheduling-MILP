from datetime import date
from solver import Solver
from printing import  save_csv, response_build, save_excel
from pulp import LpStatus
import json

def main():

    ob_weight = (50, 33, 10, 10)
    
    weekend_pattern_const = True
    from_date = date(2024, 12, 9)
    to_date = date(2025,1, 5)

    employees = ['Raffaele', 'Roberta', 'Giacomo', 'Nunzia', 'Pouya', 'Viviana', 'Bianca']
    employees_far = ['Giacomo', 'Nunzia', 'Pouya', 'Bianca']

    max_h_employee_for_day = 8 
    min_h_employee_for_day = 6
    max_h_employee_for_week = 38
    min_h_employee_for_week = 36
    max_n_split_employee_for_week = 5 
    max_n_split_employee_far_for_week = 1

    solver = Solver(from_date, to_date, employees, employees_far, max_h_employee_for_day, min_h_employee_for_day, max_n_split_employee_for_week, max_n_split_employee_far_for_week, max_h_employee_for_week, min_h_employee_for_week, ob_weight, weekend_pattern_const)
    
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
    status = solver.solve_HiGHS(timeLimit=60, gapRel = 0.05, threads=16, path='HiGHSstatic.v1.7.1.aarch64-apple-darwin/bin/highs')

    #status = solver.solve_GUROBI(timeLimit=60, gapRel = 0.05, threads=16)
    #status = solver.solve_SCIP(timeLimit=120, gapRel = 0.05, threads=16)
    #status = solver.solve_GLPK(timeLimit=120)

    print('status', LpStatus[status])

    save_csv(solver, 'calendar.csv')
    save_excel(solver, 'calendar.csv', 'calendar.xlsx')
    print(json.dumps(response_build(solver)))

if __name__ == '__main__':
    main()