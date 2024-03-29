from datetime import date
from solver import Solver, save_csv
from pulp import LpStatus

def main():
    # weight var_hours, var_leave, sum_leave, var_split, sum_split
    ob_weight = (0.33, 1, 0.33, 1, 0.33, 1, 0.33)
    #ob_weight = (0.33, 1, 0.33, 1, 0.33, 1, 10000)

    from_date = date(2024, 2, 1)
    to_date = date(2024, 2, 29)
    employees = ['Raffaele', 'Grazia', 'Nunzia', 'Roberta', 'Francesca', 'Viviana', 'Pouya', 'Chiara', 'Giacomo', 'Bianca']
    employees_senior = employees[0:5]
    max_h_employee_for_day = 9
    min_h_employee_for_day = 4

    solver = Solver(from_date, to_date, employees, employees_senior, max_h_employee_for_day, min_h_employee_for_day, ob_weight)

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

    status = solver.solve(timeLimit=40, gapRel = 0.02, threads=1)
    print('status', LpStatus[status])

    save_csv(solver, 'calendar.csv')

if __name__ == '__main__':
    main()