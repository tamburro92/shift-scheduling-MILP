from datetime import datetime, timedelta
import collections
import pulp
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD, GLPK_CMD, GUROBI_CMD, SCIP_CMD, HiGHS_CMD
import csv
'''
- Ogni impiegato puo lavorare 2 volte al giorno in turni non contigui
- Ogni impiegato lavora massimo 5 volte in 1 settimana
- Ogni impiegato deve avere un weekend di riposo ogni 4 settimane
- Se l'impiegato fa chiusura allora non fa apertura il giorno seguente
- Per l'apertura e chiusura deve esserci 1 senior presente

Personale : 'Raffaele', 'Grazia', 'Nunzia', 'Roberta', 'Francesca', 'Viviana', 'Pouya', 'Chiara', 'Giacomo', 'Bianca'
Senior: 'Raffaele', 'Grazia', 'Nunzia', 'Roberta', 'Francesca'
'''
#36h 61, w=377
slots_data = [{'from':'08:00', 'to':'14:30', 'type':'F4'},
              {'from':'08:30', 'to':'13:00', 'type':'F1'},
              {'from':'09:00', 'to':'13:00', 'type':'F1'},
              {'from':'10:00', 'to':'13:30', 'type':'F1'},
              
              {'from':'16:00', 'to':'20:00', 'type':'F2'},
              {'from':'16:00', 'to':'20:30', 'type':'F2'},
              {'from':'16:30', 'to':'20:00', 'type':'F2'},

              {'from':'13:00', 'to':'20:00', 'type':'F3'},
              {'from':'13:00', 'to':'21:00', 'type':'F3'},
              {'from':'14:30', 'to':'21:00', 'type':'F3'}]

slots_data_sat = [{'from':'08:00', 'to':'16:00', 'type':'F8'},
                      {'from':'08:30', 'to':'13:00', 'type':'F5'},
                      {'from':'09:30', 'to':'13:00', 'type':'F5'},
                      {'from':'16:00', 'to':'20:30', 'type':'F6'},
                      {'from':'17:30', 'to':'21:00', 'type':'F6'},
                      {'from':'13:00', 'to':'21:00', 'type':'F7','isClosing':True}]

slots_data_sun = [{'from':'08:00', 'to':'16:00', 'type':'F8','isOpening':True},
                      {'from':'08:30', 'to':'13:00', 'type':'F5'},
                      {'from':'09:30', 'to':'13:00', 'type':'F5'},
                      {'from':'16:00', 'to':'20:30', 'type':'F6'},
                      {'from':'17:30', 'to':'21:00', 'type':'F6'},
                      {'from':'13:00', 'to':'21:00', 'type':'F7'}]

class TimeSlot():
    def __init__(self, t_from=None, t_to=None, type=None, isOpening=False, isClosing=False, date=None, idx=None):
        self.day = date.day
        self.t_from = datetime.strptime(t_from,'%H:%M') if t_from else None
        self.t_to = datetime.strptime(t_to,'%H:%M') if t_to else None
        self.duration = (self.t_to - self.t_from).seconds / 3600 if t_from else 0
        self.type = type
        self.isOpening = isOpening
        self.isClosing = isClosing
        self.week = int(date.strftime("%V")) if date else None
        self.day_of_week = date.isoweekday() if date else None
        self.date = date
        self.idx_of_day = idx



class Solver():
    def __init__(self, from_date, to_date, employees, employees_senior, max_h_employee_for_day, min_h_employee_for_day, ob_weight = (0.3,0.2,0.3), weekend_pattern_const = False, weekend_pattern_2_gap_const = False):
        self.ob_weight = ob_weight
        self.weekend_pattern_const = weekend_pattern_const
        self.weekend_pattern_2_gap_const = weekend_pattern_2_gap_const

        self.from_date = from_date
        self.to_date = to_date
        self.num_days = (to_date - from_date).days + 1
        self.employees = employees
        self.employees_senior = employees_senior
        self.days = [i for i in range(from_date.day, to_date.day+1)]
        self.shift_types = ['F4', 'F1', 'F2', 'F3','F8','F5','F6','F7']
        self.n_shifts = [i for i in range(10)]
        self.max_h_employee_for_day = max_h_employee_for_day
        self.min_h_employee_for_day = min_h_employee_for_day

        self.__build_problem()

    def __build_problem(self):
        
        max_h_employee_for_day = self.max_h_employee_for_day
        min_h_employee_for_day = self.min_h_employee_for_day
        ob_weight = self.ob_weight
        weekend_pattern_const = self.weekend_pattern_const
        weekend_pattern_2_gap_const = self.weekend_pattern_2_gap_const
        map_slot_hours_t_i = compute_dict_slot_hours(slots_data, slots_data_sat, slots_data_sun, self.from_date, self.num_days)
        self.map_slot_hours_t_i = map_slot_hours_t_i

        days = self.days
        employees = self.employees
        employees_senior = self.employees_senior
        shift_types = self.shift_types
        n_shifts = self.n_shifts

        # variables
        shifts  = LpVariable.dicts("Shift", (days, n_shifts, employees), cat="Binary")
        min_max_hours_emp = LpVariable.dicts("min max hours employee", ['min','max'], cat='Continuous')
        leave = LpVariable.dicts('Leave', (days, employees), cat="Binary")
        min_max_split_emp = LpVariable.dicts("min max split shift day employee", ['min','max'], cat='Continuous')
        min_max_leave_emp = LpVariable.dicts("min max leave employee", ['min','max'], cat='Continuous')
        min_max_leave_sun_sat_emp = LpVariable.dicts("min max leave sunday saturday employee", ['min','max'], cat='Continuous')
        leave_gap_2_days = LpVariable.dicts("Leave today and nextday", (days[:-1], employees), cat='Binary')

        # problem
        problem = LpProblem("Shift", LpMinimize)

        # Objective: minimize variance hours for employees, variance leave days, and maximize sum leaveday
        problem +=  (min_max_hours_emp['max'] - min_max_hours_emp['min']) * ob_weight[0] +\
                    (min_max_leave_emp['max'] - min_max_leave_emp['min']) * ob_weight[1] +\
                    (min_max_split_emp['max'] - min_max_split_emp['min']) * ob_weight[3] 
            # - lpSum(leave[d][e] for e in employees for d in days) * ob_weight[2] +\
            # lpSum(split_shift_emp[d][e] for e in employees for d in days) * ob_weight[4]  
            #lpSum(diff_leave_sun_sat_emp[e] for e in employees) * ob_weight[5] +\
            #lpSum(leave_gap_2_days[d][e] for e in employees for d in days[:-1]) * ob_weight[6] 

        ## Auxilary Constraints ##
        '''# Variance
        for e in employees:
        c = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for d in days for i in self.get_indexes_shift(d) )
        problem += diff_hours_emp[e] >= c - lpSum( (shifts[d][i][ee]) * map_slot_hours_t_i[d][i].duration for ee in employees for d in days for i in self.get_indexes_shift(d))/len(employees)
        problem += diff_hours_emp[e] >=  lpSum( (shifts[d][i][ee]) * map_slot_hours_t_i[d][i].duration for ee in employees for d in days for i in self.get_indexes_shift(d))/len(employees) - c
        '''
        # Constraint 0: diff_hours_emp Compute variance for employee
        for e in employees:
            sum_hours_e = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for d in days for i in self.get_indexes_shift(d) )
            problem += min_max_hours_emp['max'] >= sum_hours_e
            problem += min_max_hours_emp['min'] <= sum_hours_e

        # Constraint 0: diff_leave_emp Compute variance for employee
        for e in employees:
            sum_leaves_e = lpSum(leave[d][e] for d in days)
            problem += min_max_leave_emp['max'] >= sum_leaves_e
            problem += min_max_leave_emp['min'] <= sum_leaves_e

        # Constraint 0: leave_day
        for d in days:
            for e in employees:
                for i in self.get_indexes_shift(d):
                    problem += shifts[d][i][e] + leave[d][e] <= 1
        
        # Constraint 0: diff_shift_emp Compute variance for employee
        for e in employees:
            sum_split_e = lpSum(shifts[d][i][e] for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][i].duration < self.min_h_employee_for_day)
            problem += min_max_split_emp['max'] >= sum_split_e
            problem += min_max_split_emp['min'] <= sum_split_e

        # Constraint 0: diff_leave_sun_sat_emp Compute variance for employee
        if ob_weight[5]:
            for e in employees:
                sum_leave_6_7_e = lpSum(leave[d][e] for d in days if map_slot_hours_t_i[d][0].day_of_week in [6, 7])
                problem += min_max_leave_sun_sat_emp['max'] >= sum_leave_6_7_e
                problem += min_max_leave_sun_sat_emp['min'] <= sum_leave_6_7_e

        # Constraint 0: leave_gap_2_days
        if ob_weight[6]:
            for e in employees:
                for d in days[:-1]:
                    problem += leave_gap_2_days[d][e] * 2 <= leave[d][e] + leave[d+1][e]
                    problem += leave_gap_2_days[d][e] >= leave[d][e] + leave[d+1][e] - 1
        
        ## Problem Constraints ##
        # Constraint 1: Each employee can only work one shift per shifttype (morning, afternoon or evening)
        for d in days:
            for e in employees:
                for t in shift_types:
                    c = lpSum( (shifts[d][i][e]) for i in self.get_indexes_shift(d,t))
                    problem += c <= 1    # this should be <= constraint!  Risks infeasibility if equality (==)

        # Constraint 2: Each employee can work 2 times in 2 different shift not contiguos the same day
        for d in days:
            for e in employees:
                c1 = lpSum( shifts[d][i][e] for i in self.get_indexes_shift(d, 'F4')+self.get_indexes_shift(d, 'F3')+self.get_indexes_shift(d, 'F1') )
                c2 = lpSum( shifts[d][i][e] for i in self.get_indexes_shift(d, 'F4')+self.get_indexes_shift(d, 'F3')+self.get_indexes_shift(d, 'F2') )

                c3 = lpSum( shifts[d][i][e] for i in self.get_indexes_shift(d, 'F8')+self.get_indexes_shift(d, 'F7')+self.get_indexes_shift(d, 'F5') )
                c4 = lpSum( shifts[d][i][e] for i in self.get_indexes_shift(d, 'F8')+self.get_indexes_shift(d, 'F7')+self.get_indexes_shift(d, 'F6') )
                problem += c1 <= 1 
                problem += c2 <= 1
                problem += c3 <= 1
                problem += c4 <= 1

        # Constraint 3: Each shift must have at least 1 employees
        for d in days:
            for i in self.get_indexes_shift(d):
                c = None
                for e in employees:
                    c += shifts[d][i][e]

                # shift that doens't exist must be = 0
                value = 0 if map_slot_hours_t_i[d][i].duration == 0 else 1
                problem += c == value # 0 or 1

        # Constraint 4: Each Employee should work a max_h and min_h for day
        for e in employees:
            for d in days:
                c = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for i in self.get_indexes_shift(d))
                problem += c <= max_h_employee_for_day * (1 - leave[d][e])
                problem += c >= min_h_employee_for_day * (1 - leave[d][e])


        # Constraint 5: Each Employee should work 5 max day in a week
        for e in employees:
            c = None
            for d in days:
                c += ( 1  - leave[d][e]) # work_day = 1 - leave
                if map_slot_hours_t_i[d][0].day_of_week == 7:
                    problem += c <= 5 
                    c = None
        
        # Constraint 6: Each Employee should have a weekend dayoff each 4 weeks 
        for e in employees:
            c = None
            for d in days:
                if map_slot_hours_t_i[d][0].day_of_week in [6,7]:
                    c += leave[d][e]
            problem += c >= 1

        # Constraint 7: Each employee if he Closing evening should not do Opening next day
        for d in range(len(days)-1):
            for e in employees:
                c1, c2 = None, None
                for i in self.get_indexes_shift(d):
                    if map_slot_hours_t_i[days[d]][i].isClosing:
                        c1+= shifts[days[d]][i][e]
                for i in self.get_indexes_shift(d+1):
                    if map_slot_hours_t_i[days[d+1]][i].isOpening:
                        c2+= shifts[days[d+1]][i][e]
                if c1 and c2:
                    problem += c1+c2 <= 1 

        # Constraint 8: For Opening and closing must be at least 1 senior
        for d in days:
            for i in self.get_indexes_shift(d):
                c1, c2 = None, None
                if map_slot_hours_t_i[d][i].isOpening:
                    c1 = lpSum(shifts[d][i][e] for e in employees_senior)
                    if c1: problem += c1 >= 1
                if map_slot_hours_t_i[d][i].isClosing:
                    c2 = lpSum(shifts[d][i][e] for e in employees_senior)
                    if c2: problem += c2 >= 1

        # Constraint 9: for each type slot should be covered by 1 senior
        for d in days:
            for t in ['F4', 'F1', 'F2', 'F3', 'F7', 'F8']:
                c = lpSum(shifts[d][i][e] for i in self.get_indexes_shift(d, t) for e in employees_senior )
                if c: problem += c >= 1

        # Constraint 10: employee in a month should have a pattern of: saturday-sunday leave, sunday leave, saturday leave
        if weekend_pattern_const:
            for e in employees:
                c1, c2 = None, None
                l_list = []
                for d in days:
                    if map_slot_hours_t_i[d][0].day_of_week in [6]:
                        c1 += leave[d][e]
                    if map_slot_hours_t_i[d][0].day_of_week in [7]:
                        c2 += leave[d][e]
                    if map_slot_hours_t_i[d][0].day_of_week in [6] and d+1 <=days[-1]:
                        l = LpVariable(f'weekend leave {d} {d+1} {e}', lowBound=0, upBound=1, cat='Binary')
                        problem += l * 2 <= leave[d][e] + leave[d+1][e]
                        problem += l >= leave[d][e] + leave[d+1][e] - 1
                        l_list.append(l)

                if c1: problem += c1 >= 2
                if c2: problem += c2 >= 2
                if l_list: problem += lpSum(l_list) >= 1
        
        # Constraint 11: employee in a month if works sunday-saturday must have 2 days of leaving in the next week
        if weekend_pattern_2_gap_const:
            for e in employees:
                l_list = []
                lw = None
                for d in days:
                    if map_slot_hours_t_i[d][0].day_of_week in [6] and d+1 <=days[-1]:
                        lw = LpVariable(f'weekend work c2 {d} {d+1} {e}', lowBound=0, upBound=1, cat='Binary')
                        problem += lw * 2 <= (1 - leave[d][e]) + (1 - leave[d+1][e]) #[0, 1]
                        problem += lw >= (1 - leave[d][e]) + (1 - leave[d+1][e]) - 1

                    elif map_slot_hours_t_i[d][0].day_of_week in [1,2,3,4] and d+1 <=days[-1]:
                        l = LpVariable(f'leave gap 2 day {d} {d+1} {e}', lowBound=0, upBound=1, cat='Binary')
                        problem += l * 2 <= leave[d][e] + leave[d+1][e]
                        problem += l >= leave[d][e] + leave[d+1][e] - 1
                        l_list.append(l)

                    if map_slot_hours_t_i[d][0].day_of_week in [5]:
                        if l_list and lw is not None:
                            problem += lpSum(l_list) >= lw
                        lw = None
                        l_list.clear()

        self.min_max_split_emp = min_max_split_emp
        self.min_max_hours_emp = min_max_hours_emp
        self.problem = problem
        self.shifts = shifts
        self.leave = leave
        self.map_slot_hours_t_i = map_slot_hours_t_i
        self.leave_gap_2_days = leave_gap_2_days

    def solve_PULP(self, timeLimit=8, gapRel = 0.02, threads=1):
        self.status = self.problem.solve(PULP_CBC_CMD(timeLimit=timeLimit, gapRel = gapRel, threads=threads))
        return self.status
    def solve_GUROBI(self, timeLimit=8, gapRel = 0.02, threads=1):
        self.status = self.problem.solve(GUROBI_CMD(timeLimit=timeLimit, gapRel = gapRel, threads=threads))
        return self.status
    def solve_GLPK(self, timeLimit=8):
        self.status = self.problem.solve(GLPK_CMD(timeLimit=timeLimit))
        return self.status
    
    def solve_HiGHS(self, timeLimit=8, gapRel = 0.02, threads=1):
        self.status = self.problem.solve(HiGHS_CMD(timeLimit=timeLimit, gapRel = gapRel, threads=threads, path='HiGHSstatic.v1.7.1.aarch64-apple-darwin/bin/highs', options=["--solver=choose"]))
        return self.status
    
    def solve_SCIP(self, timeLimit=8, gapRel = 0.02, threads=1):
        self.status = self.problem.solve(SCIP_CMD(timeLimit=timeLimit, gapRel = gapRel, threads=threads))
        return self.status

    def add_c_employee_day_leave(self, employee, day_leave):
        self.problem+= self.leave[day_leave][employee] == 1
    
    def add_c_employee_day_work(self, employee, day_leave):
        self.problem+= self.leave[day_leave][employee] == 0

    def add_c_employee_shiftDay_work(self, employee, day, shift_type, n_shift):
        self.problem+= self.shifts[day][shift_type][n_shift][employee] == 1

    def add_c_employee_shiftDay_leave(self, employee, day, shift_type, n_shift):
        self.problem+= self.shifts[day][shift_type][n_shift][employee] == 0

    def get_indexes_shift(self, day, type = None):
        ret = []
        for el in self.map_slot_hours_t_i[day].values():
            if el.idx_of_day is not None and el.idx_of_day >=0 :
                if (type and type == el.type) or not type:
                    ret.append(el.idx_of_day)
        return ret
            
def compute_dict_slot_hours(slot_week, slot_sat, slot_sun, from_date, n_day):
    map_slot_hours_t_i  = collections.defaultdict(dict)
    for d in range(0, n_day):
        dt = from_date + timedelta(days=d)
        map_slot_hours_t_i[dt.day] = dict()
        for j in range(len(slot_week)):
            map_slot_hours_t_i[dt.day][j] = TimeSlot(date=dt)
    last_type = None
    slots = None
    for d in range(0, n_day):
        j = 0
        dt = from_date + timedelta(days=d)

        if dt.isoweekday() in [6]:
            slots = slot_sat
        elif dt.isoweekday() in [7]:
            slots = slot_sun
        else:
            slots = slot_week

        for i in slots:
            map_slot_hours_t_i[dt.day][j] = TimeSlot(i['from'], i['to'], i['type'], i.get('isOpening',False), i.get('isClosing',False), dt, j)
            j+=1
    return map_slot_hours_t_i

'''
PRINT FUNCTIONS
'''
def save_csv(solver, name_csv):
    from_date, to_date = solver.from_date, solver.to_date
    days, shift_types = solver.days, solver.shift_types
    employees, n_shifts = solver.employees, solver.n_shifts
    shifts, leave = solver.shifts, solver.leave
    map_slot_hours_t_i = solver.map_slot_hours_t_i
    #split_shift_emp = solver.split_shift_emp
    leave_gap_2_days = solver.leave_gap_2_days

    #print(solver.min_max_hours_emp)

    map_e_h = {}
    map_e_leave = {}
    map_e_leave_sat_sun = {}
    map_e_spezzati = {}
    map_e_split = {}
    data = []
    # init struct
    for i in range(90):
        data.append({})
    for e in employees:
        map_e_h[e] = {}
        map_e_leave[e] = 0
        map_e_leave_sat_sun[e] = 0
        map_e_split[e] = 0
        map_e_spezzati[e] = {}
        map_e_h[e]['total'] = 0
        for w in range(int(from_date.strftime('%V')), int(to_date.strftime('%V'))+1):
            map_e_h[e][w] = 0
        for d in days:
            map_e_spezzati[e][d] = 0
    data[0]['Summary'] = ''
    
    # loop
    for d in days:
        j = 0
        # add slots
        for i in solver.get_indexes_shift(d):
            for e in employees:
                if shifts[d][i][e].varValue:
                    data[j][f'{d}:Giorno'] = d
                    data[j][f'{d}:Da'] = f'{map_slot_hours_t_i[d][i].t_from.strftime("%H:%M")} - {map_slot_hours_t_i[d][i].t_to.strftime("%H:%M")}'
                    data[j][f'{d}:Durata H'] = map_slot_hours_t_i[d][i].duration
                    data[j][f'{d}:Nome'] = e
                    
                    week = map_slot_hours_t_i[d][i].week
                    map_e_h[e]['total'] = map_slot_hours_t_i[d][i].duration + map_e_h[e]['total']
                    map_e_h[e][week] = map_slot_hours_t_i[d][i].duration + map_e_h[e][week]
                    j+=1
        # add leave days
        for e in employees:
            if leave[d][e].varValue:
                data[j][f'{d}:Giorno'] = d
                data[j][f'{d}:Da'] = 'Riposo'
                data[j][f'{d}:Nome'] = e
                map_e_leave[e] = map_e_leave[e] + 1
                if map_slot_hours_t_i[d][0].day_of_week in [6,7]:
                    map_e_leave_sat_sun[e] = map_e_leave_sat_sun[e] + 1
                j+=1

    for e in employees:
        lastday = -1
        for d in days:
            for i in solver.get_indexes_shift(d):
                if shifts[d][i][e].varValue:
                    if lastday == d:
                        map_e_split[e] = map_e_split[e] + 1
                    lastday = d

    # Add total, week hours for employee
    j+=3
    data[j]['Summary'] = 'Ore totali'
    j+=1
    for k,v in map_e_h.items():
        data[j]['Summary'] = k + ' ' + str(v)
        j+=1

    # Add total leave days for employee
    j+=2
    data[j]['Summary'] = 'Ferie totali'
    j+=1
    for k,v in map_e_leave.items():
        gap_2_days = sum(leave_gap_2_days[d][k].varValue if leave_gap_2_days[d][k].varValue is not None else 0 for d in days[:-1] ) 
        data[j]['Summary'] = '{}: {} ({}) | {}'.format(k, v, map_e_leave_sat_sun[k], gap_2_days)
        j+=1
    
    j+=2
    data[j]['Summary'] = 'Spezzati totali'
    j+=1
    for k,v in map_e_split.items():
        data[j]['Summary'] = k + ' ' + str(v)
        j+=1

    fieldnames = data[0].keys()
    with open(name_csv, 'w') as myfile:
        wr = csv.DictWriter(myfile,  fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(data)
