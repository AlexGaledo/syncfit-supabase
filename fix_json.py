import json
import glob
import os

folder = r"app/api/v1/workout_testing/full_workouts/for_seeder"

for file in glob.glob(os.path.join(folder, "*.json")):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    modified = False
    exercises_map = {}
    
    for ex in data.get("exercises", []):
        exercises_map[ex["name"]] = ex
        
    for w in data.get("plan", {}).get("workouts", []):
        for wex in w.get("exercises", []):
            extracted_by_reps = None
            extracted_by_duration = None
            
            if "is_by_reps" in wex:
                extracted_by_reps = wex.pop("is_by_reps")
                modified = True
            if "is_by_duration" in wex:
                extracted_by_duration = wex.pop("is_by_duration")
                modified = True
                
            ex_name = wex.get("exercise_name")
            if ex_name in exercises_map:
                if extracted_by_reps is not None and "is_by_reps" not in exercises_map[ex_name]:
                    exercises_map[ex_name]["is_by_reps"] = extracted_by_reps
                if extracted_by_duration is not None and "is_by_duration" not in exercises_map[ex_name]:
                    exercises_map[ex_name]["is_by_duration"] = extracted_by_duration
            
    if modified:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Updated {file}")

print("Done")
