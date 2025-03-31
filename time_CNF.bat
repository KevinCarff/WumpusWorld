@echo off
echo Running simulation 100000 cnf games

@echo off
echo Start Time: %time%
python .\multiple_cnf.py --num-games 100000
echo End Time: %time%
