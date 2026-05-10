# FitSisyo Workout Plan Hub Navigation Guide
*(Context for Chatbot)*

## 1. Trainee View (The "Workout" Tab)

The Trainee's hub focuses on managing their active workout schedules, tracking progress, and creating personal routines.

* **Accessing the Hub:** Click on the **"Workout"** icon in the bottom navigation bar.
* **Home Dashboard (index.tsx):** You will see your Weekly Goals, Current Streak, Weekly Schedule (MTWTFSS), your active "My Workout Plan" card, and lists of "Presets" or custom plans.

### Creating a Workout Plan Manually
1. Access the creation page to build a custom plan.
2. **Fill in the Plan Details:** Enter the Title, Description, select a Difficulty (Beginner/Intermediate/Advanced), set the Days Per Week, Total Duration (Minutes), and toggle if Equipment is needed.
3. Select relevant **Tags** (e.g., Weightlifting, HIIT, etc.).
4. **Add a Session:** Scroll down to the Sessions list and click the **"Add Session"** button.
5. **Session Details:** Enter the Session Title (e.g., "Leg Day"), Description, Day of the Week, and Estimated Duration. 
6. **Add Exercises:** Inside the session, click **"Add Exercise"**. This will open the exercise library. Search for and select the exercises you want to add, then confirm.
7. **Configure Sets & Reps:** For each exercise added, define the Target Sets, Reps, Duration (in seconds), and Rest Time (in seconds).
8. **Save:** Click the **"Save Plan"** button at the bottom of the screen.

### Generating a Plan with AI
1. Click the AI Generation action card / button on the main Workout screen.
2. Answer the AI's prompts regarding your fitness goals, experience, and equipment.
3. The AI will pre-fill a workout plan structure constraints. Review the generated sessions and exercises.
4. Edit any details, then click **"Save Plan"**.

### Logging & Starting a Session
* **View Plan Details:** Click on an active plan to view its schedule and sessions (`workout-plan.tsx`).
* **Start Workout:** Click to start an active workout day (`session-workout.tsx`) where you go through the exercises interactively.
* **Finish & Log:** Complete the session to trigger the logger (`workout-logger.tsx`) and summary (`workout-summary.tsx`) to update your weekly streak.

---

## 2. Trainer View (The "Plans" Tab)

The Trainer's hub focuses on creating specific assignments for connected clients and managing plan templates.

* **Accessing the Hub:** Click the **"Plans"** icon in the Trainer navigation bar.
* **Home Dashboard (index.tsx):** This screen lists **"Your Plans"** (custom programs created by you) and **"Presets"** (recommended templates). You will see floating/top actions to "Create" or "Generate" new plans.

### Creating a Workout Plan for a Trainee
1. Click the action to **Create** a new plan manually (create.tsx).
2. **Fill in the Plan Overview:** Title, Description, Difficulty, Days Per Week, Total Duration, and toggle Equipment status.
3. Select any applicable **Plan Tags**.
4. **Assign a Trainee:** Tap the **Trainee Dropdown** and select one of your connected clients to assign this specific workout plan to.
5. **Add a Session:** Scroll to the workouts section and click **"Add Session"**.
6. **Configure Session Details:** Provide a Title, Description, the specific Day of the Week, and Estimated Duration.
7. **Add Exercises:** Click **"Add Exercise"** on the session card. Browse the library, select exercises, and configure the Sets, Reps, Duration, and Rest fields according to what you want the trainee to do.
8. **Save & Assign:** Click the **"Save Plan"** button. This securely creates the plan and assigns it directly to the selected trainee.

### Viewing & Modifying Plans
1. On the Plans dashboard, click the **"View"** button on any Plan Card.
2. This opens the **Plan Details screen** (`workoutPlanDetails.tsx`) where you can review all sessions, assigned exercises, and edit attributes.