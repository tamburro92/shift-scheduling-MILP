from datetime import datetime, timedelta
import collections
import pulp
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD
import csv
'''
- Ogni impiegato puo lavorare 2 volte al giorno in turni non contigui
- Ogni impiegato lavora massimo 5 volte in 1 settimana
- Ogni impiegato deve avere un weekend di riposo goni 4 settimane
- Se l'impiegato fa chiusura allora non fa apertura il giorno seguente
- Per l'apertura e chiusura deve esserci 1 senior presente

Personale : 'Raffaele', 'Grazia', 'Nunzia', 'Roberta', 'Francesca', 'Viviana', 'Pouya', 'Chiara', 'Giacomo', 'Bianca'
Senior: 'Raffaele', 'Grazia', 'Nunzia', 'Roberta', 'Francesca'
'''
#36h 61, w=377
slots_data = [{'from':'08:00', 'to':'16:00', 'type':'M', 'isOpening':True},
              {'from':'08:00', 'to':'12:00', 'type':'M','isOpening':True},
              {'from':'08:30', 'to':'13:00', 'type':'M'},
              {'from':'09:00', 'to':'13:00', 'type':'M'},
              {'from':'10:30', 'to':'13:30', 'type':'M'},
              
              {'from':'13:00', 'to':'20:00', 'type':'A'},
              {'from':'12:00', 'to':'20:00', 'type':'A'},
              {'from':'13:00', 'to':'21:00', 'type':'A'},

              {'from':'16:00', 'to':'20:00', 'type':'E'},
              {'from':'16:00', 'to':'20:00', 'type':'E'},
              {'from':'16:00', 'to':'20:00', 'type':'E'},
              {'from':'17:30', 'to':'21:00', 'type':'E', 'isClosing':True}]

slots_data_holiday = [{'from':'08:00', 'to':'14:30', 'type':'M','isOpening':True},
                      {'from':'08:00', 'to':'16:00', 'type':'M','isOpening':True},
                      {'from':'09:00', 'to':'13:00', 'type':'M'},
                      {'from':'10:00', 'to':'13:00', 'type':'M'},
                      {'from':'14:30', 'to':'21:00', 'type':'A'},
                      {'from':'16:00', 'to':'20:00', 'type':'E'},
                      {'from':'16:00', 'to':'21:00', 'type':'E','isClosing':True}]

def main():
    num_days = 28
    num_employees = 10
    max_h_employee_for_day = 9
    min_h_employee_for_day = 4
    
    map_slot_hours_t_i = compute_dict_slot_hours(slots_data, slots_data_holiday, num_days)

    days = [i for i in range(1,num_days+1)]
    weeks = [i for i in range(1,5)]
    #employees = [f'E{i}' for i in range(num_employees)]
    employees = ['Raffaele', 'Grazia', 'Nunzia', 'Roberta', 'Francesca', 'Viviana', 'Pouya', 'Chiara', 'Giacomo', 'Bianca']
    shift_types = ['M', 'A', 'E']
    n_shifts = [i for i in range(5)]
    employees_senior = employees[0:5]


    # variables
    shifts  = LpVariable.dicts("Shift", (days, shift_types, n_shifts, employees), cat="Binary")
    diff_hours_emp = LpVariable.dicts("Variance Hours Employees", employees, cat='Continuous')
    leave = LpVariable.dicts('Leave', (days, employees), cat="Binary")

    #problem
    problem = LpProblem("Shift", LpMinimize)

    #Objective: minimize variance hours for employees
    problem += lpSum(diff_hours_emp[i] for i in employees)

    # Constraint 0: diff_hours_emp Compute variance for employee
    for e in employees:
        c = lpSum(shifts[d][t][i][e] * map_slot_hours_t_i[d][t][i].duration for d in days for t in shift_types for i in n_shifts)
        problem += diff_hours_emp[e] >= c - lpSum( (shifts[d][t][i][ee]) * map_slot_hours_t_i[d][t][i].duration for ee in employees for d in days for t in shift_types for i in n_shifts)/len(employees)
        problem += diff_hours_emp[e] >=  lpSum( (shifts[d][t][i][ee]) * map_slot_hours_t_i[d][t][i].duration for ee in employees for d in days for t in shift_types for i in n_shifts)/len(employees) - c

    # Constraint 0: leave_day
    for d in days:
        for e in employees:
            for t in  shift_types: 
                for i in n_shifts:
                    problem += shifts[d][t][i][e] + leave[d][e] <= 1

    # Constraint 1: Each employee can only work one shift per shifttype (morning, afternoon or evening)
    for d in days:
        for e in employees:
            for t in  shift_types:
                c = lpSum( (shifts[d][t][i][e]) for i in n_shifts )
                problem += c <= 1    # this should be <= constraint!  Risks infeasibility if equality (==)
    
    # Constraint 2: Each employee can work 2 times in 2 different shift not contiguos the same day
    for d in days:
        for e in employees:
            c1 = lpSum( (shifts[d]['M'][i][e]) + (shifts[d]['A'][i][e]) for i in n_shifts )
            c2 = lpSum( (shifts[d]['A'][i][e]) + (shifts[d]['E'][i][e]) for i in n_shifts )
            problem += c1 <= 1 
            problem += c2 <= 1

    # Constraint 3: Each shift must have at least 1 employees
        for d in days:
            for t in shift_types:
                for i in n_shifts:
                    c = None
                    for e in employees:
                        c += shifts[d][t][i][e]

                    # shift that doens't exist must be = 0
                    value = 0 if map_slot_hours_t_i[d][t][i].duration == 0 else 1
                    problem += c == value # 0 or 1

    # Constraint 4: Each Employee should work a max_h and min_h for day
    for e in employees:
        for d in days:
            c = lpSum(shifts[d][t][i][e] * map_slot_hours_t_i[d][t][i].duration for t in shift_types for i in n_shifts)
            problem += c <= max_h_employee_for_day * (1 - leave[d][e])
            problem += c >= min_h_employee_for_day * (1 - leave[d][e])


    # Constraint 5: Each Employee should work 5 max day in a week
    for e in employees:
        c = None
        for d in days:
            c += lpSum(leave[d][e])
            if map_slot_hours_t_i[d]['M'][0].day_of_week == 7:
                problem += c >= 2
                c = None

    # Constraint 6: Each Employee should have a weekend dayoff each 4 weeks 
    for e in employees:
        c = None
        for d in days:
            if map_slot_hours_t_i[d]['M'][0].day_of_week in [6,7]:
                c += leave[d][e]
        problem += c >= 1

    # Constraint 7: Each employee if he Closing evening should not do Opening next day
    for d in range(len(days)-1):
        for e in employees:
            c1, c2 = None, None
            for t in shift_types:
                for i in n_shifts:
                    if map_slot_hours_t_i[days[d]][t][i].isClosing:
                        c1+= shifts[days[d]][t][i][e]
                    if map_slot_hours_t_i[days[d+1]][t][i].isOpening:
                        c2+= shifts[days[d+1]][t][i][e]
            if c1 and c2:
                problem += c1+c2 <= 1 

    
    # Constraint 8: For Opening and closing must be at least 1 senior
    for d in days:
        c1, c2 = None, None
        for t in shift_types:
            for i in n_shifts:
                if map_slot_hours_t_i[d][t][i].isOpening:
                    c1 += lpSum(shifts[d][t][i][e] for e in employees_senior)
                if map_slot_hours_t_i[d][t][i].isClosing:
                    c2 += lpSum(shifts[d][t][i][e] for e in employees_senior)
        problem += c1 >= 1
        problem += c2 >= 1


    # sample dayoff
    #problem+= leave[days[0]][employees[0]] == 1

    status = problem.solve(PULP_CBC_CMD(timeLimit=5, gapRel = 0.02, threads=1))
    print('status',pulp.LpStatus[status])

    print_employee_assignment(employees, days, shift_types, n_shifts, shifts, diff_hours_emp, map_slot_hours_t_i)
    print_assignment_calendar(employees, days, shift_types, n_shifts, shifts, diff_hours_emp, leave, map_slot_hours_t_i)
    save_csv(employees, days, shift_types, n_shifts, shifts, leave, diff_hours_emp, weeks, map_slot_hours_t_i)



def compute_dict_slot_hours(slot_week, slot_weekend, n_day):
    map_slot_hours_t_i  = collections.defaultdict(dict)
    for d in range(1,n_day+1):
        map_slot_hours_t_i[d] = dict()
        for i in ['M','A','E']:
            map_slot_hours_t_i[d][i] = dict()
            for j in range(len(slot_week)):
                map_slot_hours_t_i[d][i][j] = TimeSlot(day=d)
    j = 0
    last_type = None
    slots = None
    for d in range(1,n_day+1):
        slots =  slot_weekend if d in [6,7,13,14,20,21,27,28] else slot_week
        for i in slots:
            if last_type != i['type']:
                last_type = i['type']
                j = 0
            map_slot_hours_t_i[d][i['type']][j] = TimeSlot(d, i['from'], i['to'], i['type'], i.get('isOpening',False), i.get('isClosing',False))
            j+=1
    return map_slot_hours_t_i

'''
PRINT FUNCTIONS
'''
def save_csv(employees, days, shift_types, n_shifts, shifts, leave, diff_hours_emp, weeks, map_slot_hours_t_i):
    map_e_h = {}
    map_e_leave = {}
    map_e_spezzati = {}
    data = []
    # init struct
    for i in range(60):
        data.append({})
    for e in employees:
        map_e_h[e] = {}
        map_e_leave[e] = 0
        map_e_spezzati[e] = {}
        map_e_h[e]['total'] = 0
        for w in weeks:
            map_e_h[e][w] = 0
        for d in days:
            map_e_spezzati[e][d] = 0
    data[0]['Summary'] = ''
    
    # loop
    for d in days:
        j = 0
        # add slots
        for t in shift_types:
            for i in n_shifts:
                for e in employees:
                    if shifts[d][t][i][e].varValue:
                        data[j][f'{d}:Giorno'] = d
                        data[j][f'{d}:Da'] = f'{map_slot_hours_t_i[d][t][i].t_from.strftime("%H:%M")} - {map_slot_hours_t_i[d][t][i].t_to.strftime("%H:%M")}'
                        data[j][f'{d}:Durata H'] = map_slot_hours_t_i[d][t][i].duration
                        data[j][f'{d}:Nome'] = e
                        
                        week = map_slot_hours_t_i[d][t][i].week
                        map_e_h[e]['total'] = map_slot_hours_t_i[d][t][i].duration + map_e_h[e]['total']
                        map_e_h[e][week] = map_slot_hours_t_i[d][t][i].duration + map_e_h[e][week]
                        map_e_spezzati[e][d] = map_e_spezzati[e][d] + 1
                j+=1
        # add leave days
        for e in employees:
            if leave[d][e].varValue:
                data[j][f'{d}:Giorno'] = d
                data[j][f'{d}:Da'] = 'Riposo'
                data[j][f'{d}:Nome'] = e
                map_e_leave[e] = map_e_leave[e] + 1
                j+=1

    # Add total, week hours for employee
    j+=2
    for k,v in map_e_h.items():
        data[j]['Summary'] = k + ' ' + str(v)
        j+=1

    # Add total leave days for employee
    j+=2
    for k,v in map_e_leave.items():
        data[j]['Summary'] = k + ' ' + str(v)
        j+=1
    '''
    # Add total spezzati employee
    j+=2
    for k,v in map_e_spezzati.items():
        data[j]['Summary'] = k + ' ' + str(v)
        j+=1
    '''
    fieldnames = data[0].keys()
    with open('calendar.csv', 'w') as myfile:
        wr = csv.DictWriter(myfile,  fieldnames=fieldnames)
        wr.writeheader()
        wr.writerows(data)

def print_employee_assignment(employees, days, shift_types, n_shifts, shifts, diff_hours_emp, map_slot_hours_t_i):
    t_hours = 0
    for e in employees:
        print(f'employee: {e}')
        hours = 0
        for d in days:
            for t in shift_types:
                for i in n_shifts:
                    if shifts[d][t][i][e].varValue :
                        print(f'  {d} {i} {t} ', end='')
                        hours+= map_slot_hours_t_i[d][t][i].duration
                        t_hours+= map_slot_hours_t_i[d][t][i].duration
                    #else: print('--')
        dh=0
        dh +=diff_hours_emp[e].varValue
        print(f'  hours: {hours} {dh}')

    print(f'\nTotal hours: {t_hours}')

def print_assignment_calendar(employees, days, shift_types, n_shifts, shifts, diff_hours_emp, leave, map_slot_hours_t_i):
    for d in days:
        print('\n')
        for t in shift_types:
            for i in n_shifts:
                for e in employees:
                    if shifts[d][t][i][e].varValue:
                        print(f'day: {d} - type: {t}{i} - hours: {map_slot_hours_t_i[d][t][i].duration} - {e}')
        for e in employees:
            if leave[d][e].varValue:
                print(f'day: {d} - leave:{e}')

class TimeSlot():
    def __init__(self, day=None, t_from=None, t_to=None, type=None, isOpening=False, isClosing=False):
        self.day = day
        self.t_from = datetime.strptime(t_from,'%H:%M') if t_from else None
        self.t_to = datetime.strptime(t_to,'%H:%M') if t_to else None
        self.duration = (self.t_to - self.t_from).seconds // 3600 if t_from else 0
        self.type = type
        self.isOpening = isOpening
        self.isClosing = isClosing
        self.week = (day - 1) //7 + 1 if day else None
        self.day_of_week = (day - 1) % 7 + 1 if day else None

if __name__ == '__main__':
    main()



''' version for optimize week
    diff_hours_emp = LpVariable.dicts("Variance Hours Employees", (employees, weeks), cat='Continuous')

    #Objective: minimize variance hours for employees
    for w in weeks:
        problem += lpSum(diff_hours_emp[e][w] for e in employees)
    
    # Constraint 0: diff_hours_emp Compute variance for employee for week
    for e in employees:
        for w in weeks:       
            c = lpSum(shifts[d][t][i][e] * map_slot_hours_t_i[d][t][i].duration if map_slot_hours_t_i[d][t][i].week == w else None for d in days for t in shift_types for i in n_shifts)
            problem += diff_hours_emp[e][w] >= c - lpSum( (shifts[d][t][i][ee]) * map_slot_hours_t_i[d][t][i].duration if map_slot_hours_t_i[d][t][i].week == w else None for ee in employees for d in days for t in shift_types for i in n_shifts)/len(employees)
            problem += diff_hours_emp[e][w] >=  lpSum( (shifts[d][t][i][ee]) * map_slot_hours_t_i[d][t][i].duration if map_slot_hours_t_i[d][t][i].week == w else None for ee in employees for d in days for t in shift_types for i in n_shifts)/len(employees) - c

'''