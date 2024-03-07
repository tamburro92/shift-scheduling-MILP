# shift-scheduling-MILP
A real problem of shift scheduling solved using MILP

### What is?
This is a shift planner, that takes data from main.py and returns a CSV with daily shifts for each worker.

### Problem Description
We have a front office that needs to work all days including holidays. The shifts are pre defined and can change during the week, but suppose to be most time stable and the only changing is in the weekend ( here we have less shifts to be assigned).

Each shift can overlap according to the definition and it can have a different duration like 9-13 or 10-18, also we define 3 category of shift Morning, Afternoon and Evenening, and some shifts are marked as closing or opening and require a senior employee.

We want allocate all shifts in a month to all employees.

#### A day sample

| Day 1  | 
| ------------- | 
| 08:00-16:00, Morning, opening | 
| 08:00-12:00, Morning, opening | 
| 08:30-13:00, Morning | 
| 09:00-13:00, Morning | 
| 13:00-20:00, Afternoon | 
| 13:00-21:00, Afternoon | 
| 12:00-20:00, Afternoon | 
| 16:00-20:00, Evening | 
| 16:00-20:00, Evening | 
| 16:00-20:00, Evening | 
| 17:30-21:00, Evening, closing | 

#### The constraints added are:
* Fill each time slot
* Each employee can only work one shift per shifttype (morning, afternoon or evening)
* Each employee can work 2 times in 2 different shift not contiguos the same day (i.e. morning-evenening is ok, morning-afternoon is not ok)
* Each shift must have 1 employee
* Each employee should work a MAX_H and MIN_H for day if he's not in leaving
* Each employee should work 5 max day in a week
* Each employee should have a weekend dayoff each 4 weeks 
* Each employee if he Closing evening should not do Opening next day
* For the opening and closing slot must be at least 1 senior
* Each employee can express: desidered (and not) time slot to work for a specific day and also leaving day

#### The objective is:
* Assign all slots
* Minimize variance working hours for each employees
* Maximaze number of leaving days
* Minimaze variance of leaving days


### Output

This program returns the turns for each worker during the week, according to the constraints, in a CSV file called schedule.csv.

### Execution

To run, you have to install PuLP.
Then, in shell:

    python main.py
    
It will produce a CSV with the optimal scheduling
