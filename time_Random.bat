@echo off
echo Running simulation 100000 random games

@echo off
echo Start Time: %time%
python .\multiple_random.py --num-games 100000
echo End Time: %time%
