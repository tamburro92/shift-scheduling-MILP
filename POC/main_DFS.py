from datetime import datetime, timedelta
import copy
import random
import _pickle as cPickle
from collections import deque 

N_DAY_LAST_PERSON = 2
AVG_HOURS_DIFF = 8

N_DAY_PLANNING = 7

class TimeSlot():
    def __init__(self, day, t_from, t_to, type,assigner = None):
        self.day = day
        self.t_from = datetime.strptime(t_from,'%H:%M')
        self.t_to = datetime.strptime(t_to,'%H:%M')
        self.assigner = assigner
        self.duration = self.t_to - self.t_from
        self.type = type
    def __str__(self):
        return "\n{} - {} - {} - {} - {} - {}".format(self.day, self.t_from, self.t_to, self.assigner, self.duration, self.type)
    def __repr__(self):
        return self.__str__()

class State():
    def __init__(self, slots, people):
        self.next_free_slot_idx = 0
        self.slots = slots
        self.people = people

    def __str__(self):
        valid = self.is_valid()
        res = str(valid)+'\n' + str(self.slots) 

        for k,v in self.calculate_people_hours().items():
            res += '\n {}: {}d:{}h:{}m'.format(k,v.days, v.seconds//3600, (v.seconds//60)%60)
        return res

    def next_free_slot(self):
        if self.next_free_slot_idx > len(self.slots) - 1:
            return None
        return self.slots[self.next_free_slot_idx]
    def assign_next_free_slots(self, slot):
        self.slots[self.next_free_slot_idx] = slot
        self.next_free_slot_idx +=1

    def is_valid(self):
        return self._check_is_different_slot() and self._check_is_avg_hours() and self._check_person_is_in_last_day()

    def is_an_objective(self):
        if self.next_free_slot_idx > len(self.slots) - 1:
            pt = self.calculate_people_hours()
            if len(pt.keys()) == len(self.people):
                return True
        return False

    def calculate_people_hours(self):
        pt = {}
        for s in self.slots:
            if not s.assigner:
                break
            pt[s.assigner] = s.duration + pt.get(s.assigner, timedelta(0))

        return pt

    def _check_is_avg_hours(self, avg_hours_diff = AVG_HOURS_DIFF):
        pt = self.calculate_people_hours()
        if not pt.values():
            return True
        min_v = min(pt.values())
        max_v = max(pt.values())
        if max_v - min_v > timedelta(hours=avg_hours_diff):
            return False
        return True
    
    def _check_person_is_in_last_day(self, n_day = N_DAY_LAST_PERSON):
        pt = {}
        for p in self.people:
            pt[p] = 0
        cur_day = 1
        for idx, s in enumerate(self.slots):
            if not s.assigner:
                break
            pt[s.assigner] = s.day
            cur_day = s.day
            
            #check next day
            if idx > 0 and self.slots[idx].day != self.slots[idx-1].day:
                day_ref = self.slots[idx-1].day
                for v in pt.values():
                    if day_ref-v >=n_day: return False
        
        return True

    def _check_is_different_slot(self):
        pt = {}
        day = self.slots[0].day
        for s in self.slots:
            if not s.assigner:
                break
            if s.day != day:
                day = s.day
                pt = {}
            type_assigned = pt.get(s.assigner, None)
            # controlla slot contigui
            if type_assigned == 'M' and s.type == 'A'  or type_assigned == 'A' and s.type == 'E' or  \
                type_assigned == 'A' and s.type == 'M'  or type_assigned == 'E' and s.type == 'A' or \
                type_assigned == 'A' and s.type == 'A'  or type_assigned == 'E' and s.type == 'E' or type_assigned == 'M' and s.type == 'M':
                return False
            pt[s.assigner] = s.type

        return True


slots_data = [{'from':'08:00', 'to':'16:00', 'type':'M'},
              {'from':'08:00', 'to':'12:00', 'type':'M'},
              {'from':'08:30', 'to':'13:00', 'type':'M'},
              {'from':'09:00', 'to':'13:00', 'type':'M'},
              {'from':'10:30', 'to':'13:30', 'type':'M'},
              
              {'from':'13:00', 'to':'20:00', 'type':'A'},
              {'from':'12:00', 'to':'20:00', 'type':'A'},
              {'from':'13:00', 'to':'21:00', 'type':'A'},

              {'from':'16:00', 'to':'20:00', 'type':'E'},
              {'from':'16:00', 'to':'20:00', 'type':'E'},
              {'from':'16:00', 'to':'20:00', 'type':'E'},
              {'from':'17:30', 'to':'21:00', 'type':'E'}]

slots_data_holiday = [{'from':'08:00', 'to':'14:30', 'type':'M'},
                      {'from':'08:00', 'to':'16:00', 'type':'M'},
                      {'from':'09:00', 'to':'13:00', 'type':'M'},
                      {'from':'10:00', 'to':'13:00', 'type':'M'},
                      {'from':'14:30', 'to':'21:00', 'type':'A'},
                      {'from':'16:00', 'to':'20:00', 'type':'E'},
                      {'from':'16:00', 'to':'21:00', 'type':'E'}]
people = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
def main():
    slots = []
    for i in range(1,N_DAY_PLANNING+1):
        if i == 6 or i == 7:
            for el in slots_data_holiday:
                slots.append(TimeSlot(i, el['from'],el['to'],el['type']))      
        else:
            for el in slots_data:
                slots.append(TimeSlot(i, el['from'],el['to'],el['type']))
    state = State(slots, people)
    result = solve(state)
    print(result)

def solve(state_in):
    states = deque([state_in])
    solutions = []
    while states:
        state = states.pop()
        if state.is_valid():
            if state.is_an_objective():
                return state
            next = state.next_free_slot()
            if not next:
                continue
            #random.shuffle(people)
            for p in state.people:
                new_state = cPickle.loads(cPickle.dumps(state, -1))
                new_next = cPickle.loads(cPickle.dumps(next, -1))
                new_next.assigner = p
                new_state.assign_next_free_slots(new_next)
                
                #shift 1 element heuristic
                new_state.people.append(new_state.people.pop(0))
                states.append(new_state)
    return None




if __name__ == '__main__':
    main()