from datetime import datetime, timedelta
import collections
import pulp
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD, GLPK_CMD, GUROBI_CMD, SCIP_CMD, HiGHS_CMD
import csv
import json
import copy
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

#36h 61, w=377
#F1/2 - 5/6 spezzati
slots_data = {}
slots_data[1] = [{'from':'08:00', 'to':'12:00', 'type':'F1'},
              {'from':'08:00', 'to':'14:00', 'type':'F3'},
              {'from':'09:00', 'to':'13:00', 'type':'F1', 'min_emp':7},
              {'from':'12:00', 'to':'20:00', 'type':'F3'},
              {'from':'13:00', 'to':'21:00', 'type':'F3'},
              {'from':'16:00', 'to':'20:00', 'type':'F2', 'min_emp':7},
              {'from':'17:00', 'to':'20:00', 'type':'F2'}]
slots_data[2] =[{'from':'08:00', 'to':'12:00', 'type':'F1'},
              {'from':'08:00', 'to':'14:00', 'type':'F3'},
              {'from':'09:00', 'to':'13:00', 'type':'F1', 'min_emp':7},
              {'from':'12:00', 'to':'20:00', 'type':'F3'},
              {'from':'13:00', 'to':'20:30', 'type':'F3'},
              {'from':'16:00', 'to':'20:00', 'type':'F2', 'min_emp':7},
              {'from':'17:00', 'to':'20:00', 'type':'F2'}]
slots_data[6] = [{'from':'08:00', 'to':'16:00', 'type':'F8'}, 
                {'from':'09:00', 'to':'13:00', 'type':'F5'},
                {'from':'10:00', 'to':'13:00', 'type':'F5'},
                {'from':'16:00', 'to':'20:00', 'type':'F6'},
                {'from':'16:00', 'to':'21:00', 'type':'F6'}]
slots_data[5] = slots_data[1]
slots_data[3] = slots_data[4] = slots_data[2]
slots_data[7] = slots_data[6] 

extra_slot = {'from':'13:00', 'to':'20:00', 'type':'EXTRA'}
N_EXTRA_SLOT = 1

MIP_TOLERANCE = 1e-6

FORMAT_DATE = "%d/%m/%Y"

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
    def __init__(self, from_date, to_date, employees, employees_far, max_h_employee_for_day, min_h_employee_for_day, max_n_split_employee_for_week, max_n_split_employee_far_for_week, max_h_employee_for_week, min_h_employee_for_week, ob_weight = (0.3,0.2,0.3), weekend_pattern_const = False):
        self.ob_weight = ob_weight
        self.weekend_pattern_const = weekend_pattern_const

        self.from_date = from_date
        self.to_date = to_date
        self.num_days = (to_date - from_date).days + 1
        self.employees = employees
        self.employees_far = employees_far
        self.days = [(from_date + timedelta(days=i)).strftime('%d-%m-%Y') for i in range(self.num_days)]
        self.weeks = range(int(from_date.strftime("%V")), int(to_date.strftime("%V")) + 1 )
        self.shift_types = ['F4', 'F1', 'F2', 'F3','F8','F5','F6','F7', 'EXTRA']
        self.n_shifts = [i for i in range(11)]
        self.max_h_employee_for_day = max_h_employee_for_day
        self.min_h_employee_for_day = min_h_employee_for_day
        self.max_n_split_employee_for_week = max_n_split_employee_for_week
        self.max_n_split_employee_far_for_week = max_n_split_employee_far_for_week
        self.max_h_employee_for_week = max_h_employee_for_week
        self.min_h_employee_for_week = min_h_employee_for_week

        self.__build_problem()

    def __build_problem(self):
        
        max_h_employee_for_day = self.max_h_employee_for_day
        min_h_employee_for_day = self.min_h_employee_for_day
        max_h_employee_for_week = self.max_h_employee_for_week
        min_h_employee_for_week = self.min_h_employee_for_week
        max_n_split_employee_for_week = self.max_n_split_employee_for_week
        max_n_split_employee_far_for_week = self.max_n_split_employee_far_for_week
        ob_weight = self.ob_weight
        weekend_pattern_const = self.weekend_pattern_const
        map_slot_hours_t_i = compute_dict_slot_hours(slots_data, self.employees, self.from_date, self.num_days)
        self.map_slot_hours_t_i = map_slot_hours_t_i

        days = self.days
        weeks = self.weeks
        employees = self.employees
        employees_far = self.employees_far
        shift_types = self.shift_types
        n_shifts = self.n_shifts

        # variables
        shifts  = LpVariable.dicts("Shift", (days, n_shifts, employees), cat="Binary")
        leave = LpVariable.dicts('Leave', (days, employees), cat="Binary")
        leave_gap_2_days = LpVariable.dicts("Leave today and nextday", (days[:-1], employees), cat='Binary')
        min_max_hours_emp = LpVariable.dicts("min max hours employee", ['min','max'], cat='Continuous')
        min_max_hours_emp_week = LpVariable.dicts("min max hours week employee", (['min','max'], weeks), cat='Continuous')
        min_max_split_emp = LpVariable.dicts("min max split shift day employee", ['min','max'], cat='Integer')
        min_max_split_emp_week = LpVariable.dicts("min max split shift day week employee", (['min','max'], weeks), cat='Integer')
        min_max_split_emp_far = LpVariable.dicts("min max split shift day employee far", ['min','max'], cat='Integer')

        min_max_leave_emp = LpVariable.dicts("min max leave employee", ['min','max'], cat='Integer')
        min_max_leave_emp_week = LpVariable.dicts("min max leave week employee", (['min','max'], weeks), cat='Integer')
        min_max_extra_slot = LpVariable.dicts("min max extra slot for day", ['min','max'], cat='Integer')
        variance_extra_slot = LpVariable.dicts("variance extra slot for day", days, cat='Continuous')
        
        # problem
        problem = LpProblem("Shift", LpMinimize)

        # Objective: minimize
        problem +=  lpSum(min_max_split_emp_week['max'][week] - min_max_split_emp_week['min'][week] for week in weeks) * 50 +\
                    (min_max_split_emp['max'] - min_max_split_emp['min']) * 40 +\
                    (min_max_hours_emp['max'] - min_max_hours_emp['min']) * 10 +\
                    lpSum(variance_extra_slot[d] for d in days)/len(days) * 30 +\
                    (min_max_split_emp_far['max'] - min_max_split_emp_far['min']) * 40 +\
                    - 40 * lpSum(shifts[d][i][e] for week in weeks for e in employees_far for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][i].duration < self.min_h_employee_for_day and map_slot_hours_t_i[d][0].week == week ) #sum of all split employees far
                    #( min_max_hours_emp['max']) * 40
                    #- min_max_split_emp_far['max'] * 10
                    #(min_max_split_emp['min'] - min_max_split_emp_far['min'])  * 10
                    #(min_max_extra_slot['max'] - min_max_extra_slot['min']) * 10

        ## Auxilary Constraints ##
        
        # Constraint 0: min_max_hours_emp compute min max hours
        for e in employees:
            sum_hours_e = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for d in days for i in self.get_indexes_shift(d) )
            problem += min_max_hours_emp['max'] >= sum_hours_e
            problem += min_max_hours_emp['min'] <= sum_hours_e

        # Constraint 0: min_max_leave_emp compute min max N leaving days
        for e in employees:
            sum_leaves_e = lpSum(leave[d][e] for d in days)
            problem += min_max_leave_emp['max'] >= sum_leaves_e
            problem += min_max_leave_emp['min'] <= sum_leaves_e

        # Constraint 0: leave_day
        for d in days:
            for e in employees:
                for i in self.get_indexes_shift(d):
                    problem += shifts[d][i][e] + leave[d][e] <= 1
        
        # Constraint 0: min_max_split_emp compute min max N split for each employee
        for e in set(employees) - set(employees_far):
            sum_split_e = lpSum(shifts[d][i][e] for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][i].duration < self.min_h_employee_for_day)
            problem += min_max_split_emp['max'] * 2 >= sum_split_e
            problem += min_max_split_emp['min'] * 2 <= sum_split_e

        # Constraint 0: min_max_split_emp compute min max N split for each employee
        for e in employees_far:
            sum_split_e = lpSum(shifts[d][i][e] for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][i].duration < self.min_h_employee_for_day)
            problem += min_max_split_emp_far['max'] * 2 >= sum_split_e
            problem += min_max_split_emp_far['min'] * 2 <= sum_split_e

        # Constraint 0: min_max_extra_slot compute min max extra slot for day
        for d in days:
            sum_shift_extra = lpSum(shifts[d][i][e] for i in self.get_indexes_shift(d) for e in employees if map_slot_hours_t_i[d][i].type == 'EXTRA')
            problem += min_max_extra_slot['max'] >= sum_shift_extra
            problem += min_max_extra_slot['min'] <= sum_shift_extra
        
        # Constraint 0: variance_extra_slot compute variance of extra slot for day
        for d in days:
            x = lpSum(shifts[d][i][e] for i in self.get_indexes_shift(d) for e in employees if map_slot_hours_t_i[d][i].type == 'EXTRA')
            mx = lpSum(shifts[dd][i][e] for e in employees for dd in days for i in self.get_indexes_shift(dd) if map_slot_hours_t_i[dd][i].type == 'EXTRA' )/len(days)
            problem += variance_extra_slot[d] >= x - mx
            problem += variance_extra_slot[d] >= mx - x

        # Constraint 0: same above for weeks
        for e in set(employees) - set(employees_far):
            for week in weeks:
                sum_split_week = lpSum(shifts[d][i][e] for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][i].duration < self.min_h_employee_for_day and map_slot_hours_t_i[d][0].week == week)
                problem += min_max_split_emp_week['max'][week] >= sum_split_week
                problem += min_max_split_emp_week['min'][week] <= sum_split_week
        
        for e in employees:
            for week in weeks:
                sum_leaves_week = lpSum(leave[d][e] for d in days if map_slot_hours_t_i[d][0].week == week)
                problem += min_max_leave_emp_week['max'][week] >= sum_leaves_week
                problem += min_max_leave_emp_week['min'][week] <= sum_leaves_week

        for e in employees:
            for week in weeks:
                sum_hours_week = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][0].week == week)
                problem += min_max_hours_emp_week['max'][week] >= sum_hours_week
                problem += min_max_hours_emp_week['min'][week] <= sum_hours_week
        
        '''
        # Constraint 0: leave_gap_2_days compute N of 2 continuous leaving days
        for e in employees:
            for d in days[:-1]:
                problem += leave_gap_2_days[d][e] * 2 <= leave[d][e] + leave[d+1][e]
                problem += leave_gap_2_days[d][e] >= leave[d][e] + leave[d+1][e] - 1
        '''
        #
        ## Problem Constraints ##
        # Constraint 1: Each employee can only work one shift per shifttype (morning, afternoon or evening)
        for d in days:
            for e in employees:
                for t in shift_types:
                    c = lpSum( (shifts[d][i][e]) for i in self.get_indexes_shift(d,t))
                    problem += c <= 1

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
                
                # skip EXTRA slots
                if map_slot_hours_t_i[d][i].type == 'EXTRA':
                    continue

                # shift that doens't exist must be = 0
                value = 0 if map_slot_hours_t_i[d][i].duration == 0 else 1
                problem += c == value # 0 or 1

        # Constraint 4: Each Employee should work a max_h and min_h for day
        for e in employees:
            for d in days:
                c = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for i in self.get_indexes_shift(d))
                problem += c <= max_h_employee_for_day * (1 - leave[d][e])
                problem += c >= min_h_employee_for_day * (1 - leave[d][e])
       
        # Constraint 4: Each Employee should work a max_h and min_h for week
        for e in employees:
            for week in weeks:
                sum_hours_week = lpSum(shifts[d][i][e] * map_slot_hours_t_i[d][i].duration for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][0].week == week)
                problem += sum_hours_week >= min_h_employee_for_week
                problem += sum_hours_week <= max_h_employee_for_week

        # Constraint 4: Each Employee should do max N split for week
        for e in employees:
            for week in weeks:
                sum_split_e = lpSum(shifts[d][i][e] for d in days for i in self.get_indexes_shift(d) if map_slot_hours_t_i[d][i].duration < self.min_h_employee_for_day and map_slot_hours_t_i[d][0].week == week)
                if e in employees_far:
                    problem += sum_split_e <= max_n_split_employee_far_for_week * 2
                else:
                    problem += sum_split_e <= max_n_split_employee_for_week * 2


        # Constraint 5: Each Employee should work exactly 5 days in a week
        for e in employees:
            for week in weeks:
                c = lpSum(( 1  - leave[d][e]) for d in days if map_slot_hours_t_i[d][0].week == week) # work_day = 1 - leave
                problem += c == 5 
        
        # Constraint 6: Each Employee should have a weekend dayoff each 4 weeks (in a month)
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
        
        # Constraint 10: employee in a month should have a pattern of: saturday-sunday leave, sunday leave, saturday leave
        if weekend_pattern_const:
            for e in employees:
                c1, c2 = None, None
                l_list = []
                for idx, d in enumerate(days):
                    if map_slot_hours_t_i[d][0].day_of_week in [6]:
                        c1 += leave[d][e]
                    if map_slot_hours_t_i[d][0].day_of_week in [7]:
                        c2 += leave[d][e]
                    if map_slot_hours_t_i[d][0].day_of_week in [6] and idx+1 < len(days):
                        l = LpVariable(f'weekend leave {d} {days[idx+1]} {e}', lowBound=0, upBound=1, cat='Binary')
                        problem += l * 2 <= leave[d][e] + leave[days[idx+1]][e]
                        problem += l >= leave[d][e] + leave[days[idx+1]][e] - 1
                        l_list.append(l)

                #if c1: problem += c1 >= 2
                #if c2: problem += c2 >= 2
                if c1: problem += c1 == 2
                if c2: problem += c2 == 2
                if l_list: problem += lpSum(l_list) >= 1
        

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
        self.status = self.problem.solve(HiGHS_CMD(timeLimit=timeLimit, gapRel = gapRel, threads=threads, path='HiGHSstatic.v1.7.1.aarch64-apple-darwin/bin/highs', options=[f"mip_feasibility_tolerance = {MIP_TOLERANCE}"]))
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

    def add_c_employee_shiftType_leave(self, employee, day, shift_type):
        c = lpSum(self.shifts[day][i][employee] for i in self.get_indexes_shift(day, shift_type))   
        self.problem+= c == 0

    def get_indexes_shift(self, day, type = None):
        ret = []
        for el in self.map_slot_hours_t_i[day].values():
            if el.idx_of_day is not None and el.idx_of_day >=0 :
                if (type and type == el.type) or not type:
                    ret.append(el.idx_of_day)
        return ret
    
    def get_indexes_group_by_week(self):
        ret = {}
        for d in self.days:
            n_week = self.map_slot_hours_t_i[d][0].week
            if n_week not in ret:
                ret[n_week] = []
            ret[n_week].append(d)
        return ret
            
def compute_dict_slot_hours(slot_data, employees, from_date, n_day):
    slot_week = copy.deepcopy(slot_data)
    for key in slot_week:
        slot_week[key] = [slot for slot in slot_week[key] if 'min_emp' not in slot or len(employees)>=slot['min_emp']]

    n_extra_slot = N_EXTRA_SLOT
    map_slot_hours_t_i  = collections.defaultdict(dict)
    
    days = [(from_date + timedelta(days=i)).strftime('%d-%m-%Y') for i in range(n_day)]
    for d in days:
        dt = datetime.strptime(d, '%d-%m-%Y')

        map_slot_hours_t_i[d] = dict()
        for j in range(len(slot_week[1]) + n_extra_slot):
            map_slot_hours_t_i[d][j] = TimeSlot(date=dt)
    last_type = None
    slots = None
    for d in days:
        dt = datetime.strptime(d, '%d-%m-%Y')
        j = 0

        slots = slot_week.get(dt.isoweekday(), slot_week[1])

        for i in slots:
            map_slot_hours_t_i[d][j] = TimeSlot(i['from'], i['to'], i['type'], i.get('isOpening',False), i.get('isClosing',False), dt, j)
            j+=1

        for _ in range(n_extra_slot):
            i = extra_slot
            map_slot_hours_t_i[d][j] = TimeSlot(i['from'], i['to'], i['type'], i.get('isOpening',False), i.get('isClosing',False), dt, j)
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
        map_e_leave[e] = {}
        map_e_leave_sat_sun[e] = 0
        map_e_split[e] = 0
        map_e_spezzati[e] = {}
        map_e_h[e]['total'] = 0
        map_e_leave[e]['total'] = 0
        for w in range(int(from_date.strftime('%V')), int(to_date.strftime('%V'))+1):
            map_e_h[e][w] = 0
            map_e_leave[e][w] = 0
        for d in days:
            map_e_spezzati[e][d] = 0
    data[0]['Summary'] = ''
    
    # loop
    for d in days:
        j = 0
        # add slots
        for i in solver.get_indexes_shift(d):
            for e in employees:
                if abs(1 - shifts[d][i][e].varValue) <= MIP_TOLERANCE:
                    data[j][f'{d}:Giorno'] = d
                    data[j][f'{d}:Da'] = f'{map_slot_hours_t_i[d][i].t_from.strftime("%H:%M")} - {map_slot_hours_t_i[d][i].t_to.strftime("%H:%M")}'
                    data[j][f'{d}:Durata H'] = map_slot_hours_t_i[d][i].duration
                    data[j][f'{d}:Tipo'] = map_slot_hours_t_i[d][i].type
                    
                    data[j][f'{d}:Nome'] = e
                    
                    week = map_slot_hours_t_i[d][i].week
                    map_e_h[e]['total'] = map_slot_hours_t_i[d][i].duration + map_e_h[e]['total']
                    map_e_h[e][week] = map_slot_hours_t_i[d][i].duration + map_e_h[e][week]
                    j+=1

        # add leave days
        for e in employees:
            if abs(1 - leave[d][e].varValue) <= MIP_TOLERANCE:
                data[j][f'{d}:Giorno'] = d
                data[j][f'{d}:Da'] = 'Riposo'
                data[j][f'{d}:Nome'] = e


                week = map_slot_hours_t_i[d][i].week
                map_e_leave[e]['total'] = map_e_leave[e]['total'] + 1
                map_e_leave[e][week] = map_e_leave[e][week] + 1
                if map_slot_hours_t_i[d][0].day_of_week in [6,7]:
                    map_e_leave_sat_sun[e] = map_e_leave_sat_sun[e] + 1
                j+=1

    for e in employees:
        lastday = -1
        for d in days:
            for i in solver.get_indexes_shift(d):
                if abs(1 - shifts[d][i][e].varValue) <= MIP_TOLERANCE:
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
        #gap_2_days = sum(leave_gap_2_days[d][k].varValue if leave_gap_2_days[d][k].varValue is not None else 0 for d in days[:-1] ) 
        data[j]['Summary'] = '{}: {} ({}) '.format(k, v, map_e_leave_sat_sun[k])
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

def response_build(solver):
    from_date, to_date = solver.from_date, solver.to_date
    days, shift_types = solver.days, solver.shift_types
    employees, n_shifts = solver.employees, solver.n_shifts
    shifts, leave = solver.shifts, solver.leave
    map_slot_hours_t_i = solver.map_slot_hours_t_i
    #split_shift_emp = solver.split_shift_emp
    leave_gap_2_days = solver.leave_gap_2_days


    response = {}
    scheduling = {}
    response['scheduling'] = scheduling
    # loop
    for d in days:
        j = 0
        # add slots
        for i in solver.get_indexes_shift(d):
            for e in employees:
                if abs(1 - shifts[d][i][e].varValue) <= MIP_TOLERANCE:
                    date_str = map_slot_hours_t_i[d][i].date.strftime(FORMAT_DATE)
                    shift = {}
                    shift['giorno'] = map_slot_hours_t_i[d][i].date.strftime(FORMAT_DATE)
                    shift['da'] = f'{map_slot_hours_t_i[d][i].t_from.strftime("%H:%M")} - {map_slot_hours_t_i[d][i].t_to.strftime("%H:%M")}'
                    shift['durata'] = map_slot_hours_t_i[d][i].duration
                    shift['tipo'] = map_slot_hours_t_i[d][i].type
                    shift['nome'] = e
                    if date_str not in scheduling:
                         scheduling[date_str] = []
                    scheduling[date_str].append(shift)              

        # add leave days
        for e in employees:
            if abs(1 - leave[d][e].varValue) <= MIP_TOLERANCE:
                    date_str = map_slot_hours_t_i[d][i].date.strftime(FORMAT_DATE)
                    shift = {}
                    shift['giorno'] = map_slot_hours_t_i[d][0].date.strftime(FORMAT_DATE)
                    shift['da'] = ''
                    shift['durata'] = ''
                    shift['tipo'] = 'Riposo'
                    shift['nome'] = e
                    if date_str not in scheduling:
                         scheduling[date_str] = []
                    scheduling[date_str].append(shift)   
    
    return json.dumps(response)


    