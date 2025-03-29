@echo off
echo Running simulation for every .pkl file found in the current directory.
for %%f in (*.pkl) do (
    echo Running simulation with world file: %%f
    python cnf_game.py --load "%%f" --debug
)
echo Finished running all available .pkl files.
pause
