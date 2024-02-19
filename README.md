# shift-scheduling-MILP
A real problem of shift scheduling solved using MILP

### What is?
This is a shift planner, that takes data from main.py and returns a CSV with daily shifts for each worker.

### Problem Description
We have a front office that needs to work all days including holidays. The shifts are pre defined and can change during the week, but suppose to be most time stable and the only changing is in the weekend ( here we have less shifts to be assigned).

Each shift can overlappy according to the definition and it can have a different duration like 9-13 or 10-18, also we define 3 category of shift Morning, Afternoon and Evenening, and some shifts are marked as closing or opening and require a senior employee.

We want allocate all shifts in a month to all employees.

#### The constraints added are:
* Fill each time slot
* Each employee can only work one shift per shifttype (morning, afternoon or evening)
* Each employee can work 2 times in 2 different shift not contiguos the same day (i.e. morning-evenening is ok, morning-afternoon is not ok)
* Each shift must have 1 employees
* Each Employee should work a MAX_H and MIN_H for day if he's not in leaving
* Each Employee should work 5 max day in a week
* Each Employee should have a weekend dayoff each 4 weeks 
* Each employee if he Closing evening should not do Opening next day
* For Opening and closing must be at least 1 senior

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
