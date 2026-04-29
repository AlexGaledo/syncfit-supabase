# Workout API Integration Guide

## 1. Workout Hub Index Page

**Description:**
The Workout Hub Index Page is the central dashboard for users to view their current progress, ongoing workout statistics, active weekly schedule, and details about their current workout plan. It also provides quick access to create new plans manually or via AI.

### Component A: Number of Streak

#### Description

Displays the user's historical and currently active workout streak status, along with total metrics like minutes trained and completed workouts.

#### Endpoint: `[GET] /workout/stats/my-stats`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
{
	"trainee_id": "123e4567-e89b-12d3-a456-426614174000",
	"total_workouts_done": 15,
	"current_streak": 3,
	"longest_streak": 10,
	"total_minutes_trained": 600,
	"last_workout_log_id": 42,
	"message": "Stats retrieved successfully"
}
```

### Component B: Weekly Goal

#### Description

Fetches the active workout schedule mapped out for the current week. It includes data on how many workout days are required, and exactly which days have already been completed (`is_done`).

#### Endpoint: `[GET] /workout/workout-plans/my-schedule`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
{
	"plan_id": 1,
	"days_per_week": 3,
	"days_done_this_week": 1,
	"schedule": [
		{
			"workout_id": 101,
			"workout_title": "Monday: Push and Lower Body Focus",
			"day_of_week_int": 1,
			"day_of_week_string": "Monday",
			"order_index": 1,
			"is_done": true
		},
		{
			"workout_id": 102,
			"workout_title": "Wednesday: Pull and Posterior Chain Focus",
			"day_of_week_int": 3,
			"day_of_week_string": "Wednesday",
			"order_index": 2,
			"is_done": false
		},
		{
			"workout_id": 103,
			"workout_title": "Friday: Leg Day",
			"day_of_week_int": 5,
			"day_of_week_string": "Friday",
			"order_index": 3,
			"is_done": false
		}
	]
}
```

### Component C: My Workout Plan

#### Description

Shows the overview/metadata of the user's own workout plan, alongside pulling specific data tailored for today's session. Upon clicking this component, it should redirect to the Workout Plan Page (detailed view).

#### Endpoint 1: `[GET] /workout/workout-plans/my-workout-plan`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
{
	"plan_id": 1,
	"title": "Home Muscle Building Program",
	"description": "A bodyweight-focused hypertrophy program...",
	"duration_minutes": 45,
	"difficulty": "beginner",
	"days_per_week": 3,
	"ai_generated": true,
	"is_preset": false,
	"is_equipment_needed": false,
	"image_url": null,
	"created_by": "123e4567-e89b-12d3-a456-426614174000",
	"tags": ["muscle building focus", "full body split"],
	"workouts": [
		{
			"workout_id": 101,
			"title": "Monday: Push and Lower Body Focus",
			"description": "Focus on compound push and squat patterns.",
			"estimated_duration_minutes": 45,
			"day_of_week": 1,
			"order_index": 1,
			"exercises": [
				{
					"exercise_id": 247,
					"name": "Push Up",
					"description": "A classic bodyweight exercise.",
					"instruction": "Keep your core tight.",
					"is_equipment_needed": false,
					"video_url": "https://example.com/pushup.mp4",
					"image_url": "https://example.com/pushup.jpg",
					"tags": ["chest", "triceps"],
					"sets": 3,
					"reps": 12,
					"is_by_reps": true,
					"is_by_duration": false,
					"duration_seconds": 0,
					"rest_duration_seconds": 60,
					"order_index": 1
				}
			]
		}
	]
}
```

#### Endpoint 2: `[GET] /workout/workout-plans/today-workout`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
{
	"workout_id": 101,
	"title": "Monday: Push and Lower Body Focus",
	"description": "Focus on compound push and squat patterns.",
	"estimated_duration_minutes": 45,
	"day_of_week": 1,
	"order_index": 1,
	"exercises": [
		{
			"exercise_id": 247,
			"name": "Push Up",
			"is_equipment_needed": false,
			"tags": ["chest"],
			"sets": 3,
			"reps": 12,
			"is_by_reps": true,
			"is_by_duration": false,
			"duration_seconds": 0,
			"rest_duration_seconds": 60,
			"order_index": 1
		}
	],
	"message": "No workouts are scheduled for this plan." // (Only returned if today is a Rest Day)
}
```

### Component D: Create/Generate Workout Plan Buttons

#### 1. Create Manually Button

##### Description

(Upon click, redirect to Create Workout Plan Page)

#### 2. Generate with AI Button

##### Description

(Upon click, redirect to AI-Generate Workout Plan Page)

### Component E: Workout Plan Presets

#### Description

Displays a list of predefined (preset) workout plans available to all users. Users can browse these plans and choose to assign one to themselves.

#### Endpoint: `[GET] /workout/workout-plans?is_preset=true`

**Payload Schema:**

```json
// No payload required
// Note: Optional query parameters can be used (e.g., skip, limit, title, difficulty, days_per_week, is_equipment_needed, plan_tags).
```

**Response Schema:**

```json
[
	{
		"title": "Beginner Bodyweight Routine",
		"description": "A perfect starting point for fitness.",
		"duration_minutes": 30,
		"difficulty": "beginner",
		"days_per_week": 3,
		"ai_generated": false,
		"is_preset": true,
		"is_equipment_needed": false,
		"image_url": "https://example.com/beginner_plan.png",
		"id": 1,
		"created_by": null,
		"tags": ["full body split", "strength training focus"],
		"created_at": "2026-04-29T10:00:00Z",
		"updated_at": null
	},
	{
		"title": "Advanced Hypertrophy Focus",
		"description": "A 5-day split designed for advanced users.",
		"duration_minutes": 60,
		"difficulty": "advanced",
		"days_per_week": 5,
		"ai_generated": false,
		"is_preset": true,
		"is_equipment_needed": true,
		"image_url": "https://example.com/advanced_plan.png",
		"id": 2,
		"created_by": null,
		"tags": ["full body split", "strength training focus"],
		"created_at": "2026-04-29T10:00:00Z",
		"updated_at": "2026-04-29T12:00:00Z"
	}
]
```

## 2. Workout Plan Page

**Description:**
A detailed view of a workout plan displaying the plan's metadata and a list of its workout sessions (without eagerly showing all associated exercises on the UI level). This page acts as the central hub for a specific plan, whether it's the user's actively assigned plan ("My Workout Plan") or another plan (like a preset) being previewed.

### Endpoints Overview:

Depending on context, you will call one of two endpoints to populate Component A and Component B:

- **My Workout Plan**: `[GET] /workout/workout-plans/my-workout-plan`
- **Any Other Plan**: `[GET] /workout/workout-plans/{plan_id}/full`

**Payload Schema:**

```json
// No payload required for either endpoint
```

**Response Schema (Applies to both endpoints above):**

```json
{
	"plan_id": 1,
	"title": "Home Muscle Building Program",
	"description": "A bodyweight-focused hypertrophy program...",
	"duration_minutes": 45,
	"difficulty": "beginner",
	"days_per_week": 3,
	"ai_generated": true,
	"is_preset": false,
	"is_equipment_needed": false,
	"image_url": null,
	"created_by": "123e4567-e89b-12d3-a456-426614174000",
	"tags": ["muscle building focus", "full body split"],
	"workouts": [
		{
			"workout_id": 101,
			"title": "Monday: Push and Lower Body Focus",
			"description": "Focus on compound push and squat patterns.",
			"estimated_duration_minutes": 45,
			"day_of_week": 1,
			"order_index": 1,
			"exercises": [
				// (An array of FullExerciseDetail. You do not need to display these immediately unless expanded)
			]
		}
	]
}
```

### Component A: Workout Plan Metadata

#### Description

Displays the top-level details of the workout plan (e.g., Title, Description, Difficulty, Duration, Tags, Equipment Needed).
_Note: No separate endpoint call is required here, the data is sourced directly from the response of the primary Endpoints Overview above._

### Component B: Workout Sessions

#### Description

Displays a list or grid of the individual workout sessions included in the plan (`workouts` array). You should display the `title`, `description`, `estimated_duration_minutes`, and mapped `day_of_week`. Upon clicking a workout session, it redirects the user to the inner Workout Session Page.
_Note: No separate endpoint call is required here, the data is sourced directly from the `workouts` array in the primary Endpoints Overview response above._

### Component C: Today's Workout

#### Description

_(Only appears if this view is loaded in the "My Workout Plan" mode)._ Shows the metadata for today's scheduled workout based on the current day of the week.

#### Endpoint: `[GET] /workout/workout-plans/today-workout`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
{
	"workout_id": 101,
	"title": "Monday: Push and Lower Body Focus",
	"description": "Focus on compound push and squat patterns.",
	"estimated_duration_minutes": 45,
	"day_of_week": 1,
	"order_index": 1,
	"exercises": [
		{
			"exercise_id": 247,
			"name": "Push Up",
			"description": "A classic bodyweight exercise.",
			"instruction": "Keep your core tight.",
			"is_equipment_needed": false,
			"video_url": "https://example.com/pushup.mp4",
			"image_url": "https://example.com/pushup.jpg",
			"tags": ["chest"],
			"sets": 3,
			"reps": 12,
			"is_by_reps": true,
			"is_by_duration": false,
			"duration_seconds": 0,
			"rest_duration_seconds": 60,
			"order_index": 1
		}
	]
}
```

_(Note: If today is a rest day or nothing is scheduled, the response will return `workout_id: null` with the title "Rest Day" and a `message` key string.)_

### Component D: Start Workout Button

#### Description

A primary call-to-action button that starts today's workout. It redirects to the Workout Logger (Active Session) Page. It relies on extracting the `workout_id` from the **Component C** `today-workout` endpoint above to know which session it's initializing.

## 3. Workout Session Page

**Description:**
A specialized page managing a singular workout session. By default, it operates in read-only mode to view metadata and exercise associations. If the workout plan belongs to the user, they gain the ability to toggle an "Edit Mode" which morphs the fields into editable forms and exposes additional Add / Save actions.

### Endpoint Overview (Fetching Data): `[GET] /workout/workouts/{workout_id}/full`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
// This response matches the FullWorkoutDetail schema
{
	"workout_id": 101,
	"title": "Monday: Push and Lower Body Focus",
	"description": "Focus on compound push and squat patterns.",
	"estimated_duration_minutes": 45,
	"day_of_week": 1,
	"order_index": 1,
	"exercises": [
		{
			"exercise_id": 247,
			"name": "Push Up",
			"description": "A classic bodyweight exercise.",
			"instruction": "Keep your core tight.",
			"is_equipment_needed": false,
			"video_url": "https://example.com/pushup.mp4",
			"image_url": "https://example.com/pushup.jpg",
			"tags": ["chest"],
			"sets": 3,
			"reps": 12,
			"is_by_reps": true,
			"is_by_duration": false,
			"duration_seconds": 0,
			"rest_duration_seconds": 60,
			"order_index": 1
		}
	]
}
```

### Component A: Workout Session Metadata

Displays `title`, `description`, and `estimated_duration_minutes` retrieved from the `[GET] /workout/workouts/{workout_id}/full` endpoint.

### Component B: List of Exercises

Displays the `exercises` array from the endpoint. Provide a visually streamlined summary: show `name`, `sets`, `reps`/`duration_seconds`, `rest_duration_seconds`, `is_equipment_needed` icon, and the `image_url`.

_(Note: Hide `description`, `instruction`, and `video_url` from this immediate UI. They will be displayed when the user clicks the exercise tile to redirect to the Exercise Details page.)_

### Component C: Edit Button (Edit Workout Session)

A conditional toggle (visible if the workout session belongs to the user's workout plan). Clicking this morphs Component A and Component B fields into numerical/text inputs.

- Metadata inputs override: `title`, `description`, `estimated_duration_minutes`.
- Exercise inputs override: `sets`, `reps`, `duration_seconds`, `rest_duration_seconds`.

### Component D: Add Exercise and Save Workout Buttons

_(Only visible during Edit Mode)_

#### 1. Add Exercise Button

Redirects user to the "Add/Replace Exercise Page" (an Exercise Search Interface). The search feature retrieves data using `[GET] /workout/exercises`. Selecting an exercise injects it into the current workout array before completing the save.

#### 2. Save Workout Button

Finalizes the changes made during Edit Mode. This endpoint replaces the session metadata AND aggressively re-syncs the exercise list mapping.

**Endpoint:** `[PATCH] /workout/workouts/{workout_id}/full`

**Payload Schema:**

```json
{
	"title": "Monday: Push and Lower Body Focus (Edited)",
	"description": "Updated focus on push mechanics.",
	"estimated_duration_minutes": 55,
	"exercises": [
		{
			"exercise_id": 247,
			"sets": 4, // Changed from 3 to 4
			"reps": 15, // Changed from 12 to 15
			"duration_seconds": 0,
			"rest_duration_seconds": 60
		},
		{
			"exercise_id": 305, // A brand new exercise added via Component D-1
			"sets": 3,
			"reps": 10,
			"duration_seconds": 0,
			"rest_duration_seconds": 90
		}
	]
}
```

**Response Schema:**

```json
// Returns the updated FullWorkoutDetail structure (identical structure to the Component Overview GET Response)
{
  "workout_id": 101,
  "title": "Monday: Push and Lower Body Focus (Edited)",
  ...
}
```

## 4. Exercise Details Page

**Description:**
A dedicated page that displays the comprehensive details of a specific exercise. This page uses the `video_url` (YouTube embed) for demonstration but explicitly excludes the `image_url` in this view.

### Component A: Exercise Details

#### Description

Displays the specific details of an exercise including name, description, instruction, and the embedded video tutorial. The data for this page can either be passed locally from the `FullExerciseDetail` object retrieved in the Workout Plan / Workout Session pages, or fetched independently using the endpoint below.

#### Endpoint: `[GET] /workout/exercises/{exercise_id}`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
{
	"name": "Push Up",
	"description": "A classic bodyweight exercise.",
	"instruction": "Keep your core tight.",
	"is_equipment_needed": false,
	"video_url": "https://example.com/pushup.mp4",
	"image_url": "https://example.com/pushup.jpg",
	"is_by_reps": true,
	"is_by_duration": false,
	"id": 247,
	"created_at": "2026-04-29T10:00:00Z"
}
```

## 5. Workout Logger (Active Session Page)

**Description:**
The active interface used by the trainee while working out. It controls the progression of the session from the first exercise to the last based on the `order_index`. It calculates rest periods and records the precise Start and End datetime timestamps of the session.

### Core Workflow:

The page initializes by using the payload retrieved from `[GET] /workout/workout-plans/today-workout` (or `[GET] /workout/workouts/{workout_id}/full`).
The frontend tracks the `start_datetime` when the workout begins. When the user completes the final exercise in the UI, the frontend captures the `end_datetime` and submits the data to the Finish Workout endpoint, which redirects to the Finish Workout Summary Page.

### Component A: Exercise/Rest State

#### Description

Displays the active exercise's `name` and physical requirements (`sets` and `reps` / `duration_seconds`). After an exercise is completed, the interface transitions to a "Rest State" timer based on the `rest_duration_seconds` of the completed exercise before proceeding to the next exercise block.

### Component B: Session Navigation Controls (Previous, Play, Next)

#### Description

Manages the pacing of the active session.

1. **Previous Button:** Reverts to the previous exercise block (uses the `order_index`).
2. **Play Button:** Initiates the auto-timer for the current block (only applicable during "Rest State" or if an exercise is `is_by_duration=true`).
3. **Next Button:** Advances to the next exercise or rest block.

_Note: Once the final block is marked "Next", the frontend triggers the Completion action below (Finished Workout Summary Page)._

## 6. Finished Workout Summary Page

**Description:**
A summary screen that validates the completion of the active workout session. It posts the final timing data to the backend to officially record the log, update user statistics (like streaks), and returns the results for playback on the UI.

### Component A: Post-Workout Metrics & Streak

#### Description

Records the workout and retrieves updated global stats (Total Exercises, Duration, Streaks) based on the session's duration.

#### Endpoint: `[POST] /workout/logs/finish-workout`

**Payload Schema:**

```json
{
	"plan_id": 1, // Include if tied to a specific plan (Optional)
	"workout_id": 101, // The ID of the session just completed
	"start_datetime": "2026-04-29T10:00:00.000Z",
	"end_datetime": "2026-04-29T10:45:00.000Z"
}
```

**Response Schema:**

```json
{
	"message": "Workout logged and user stats updated successfully.",
	"workout_log": {
		"trainee_id": "123e4567-e89b-12d3-a456-426614174000",
		"plan_id": 1,
		"workout_id": 101,
		"start_datetime": "2026-04-29T10:00:00Z",
		"end_datetime": "2026-04-29T10:45:00Z",
		"duration_minutes": 45,
		"total_exercises_completed": 6,
		"id": 42
	},
	"stats": {
		"trainee_id": "123e4567-e89b-12d3-a456-426614174000",
		"total_workouts_done": 16,
		"current_streak": 4,
		"longest_streak": 10,
		"total_minutes_trained": 645,
		"last_workout_log_id": 42
	}
}
```

### Component B: Exercises Done

#### Description

Displays a recap list of all the exercises that were completed during the recently finished workout. (This data is carried over via local frontend state from the Active Session Page).

## 7. Create Workout Plan Page

**Description:**
A comprehensive form to build a customized workout plan and schedule from scratch. The data is entirely managed in local frontend state while the user builds the plan, adding sessions and mapping exercises. It is submitted via a single master endpoint once complete.

### Component A: Workout Plan Metadata & Tags

#### Description

Input fields for the plan's high-level details (`title`, `description`, `difficulty`, `days_per_week`). The user can also attach tags to the plan by querying the available global plan tags.

#### Endpoint (Fetch Available Plan Tags): `[GET] /workout/plan-tags`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
[
	{
		"id": 1,
		"name": "hypertrophy"
	},
	{
		"id": 2,
		"name": "strength"
	}
]
```

### Component B: Workout Sessions

Displays the list of workout sessions the user has created locally so far. Starts empty. Clicking a session opens the "Create Workout Session Page" (or Edit mode) to modify it.

### Component C: Form Action Buttons (Add Session & Save Plan)

#### 1. Add Workout Session Button

Redirects to the Create Workout Session Page. Note: No backend endpoint is called here. Data is simply appended to the frontend array holding the draft plan.

#### 2. Save Workout Plan Button

Commits the locally built workout plan to the database and automatically assigns it to the current user. There are two endpoints to use:

**Step 1: Save the Workout Plan**
**Endpoint:** `[POST] /workout/workout-plans/create-full`

**Payload Schema:**

```json
{
	"title": "My Custom Hypertrophy Plan",
	"description": "4-day upper/lower split focusing on high volume.",
	"duration_minutes": 240, // Optional: total estimated duration for week
	"difficulty": "intermediate",
	"days_per_week": 4,
	"ai_generated": false,
	"is_preset": false,
	"is_equipment_needed": true,
	"tags": ["push/pull/leg split"],
	"workouts": [
		{
			"title": "Monday: Upper Body Volume",
			"description": "Chest and back focus.",
			"estimated_duration_minutes": 60,
			"order_index": 1, // Required: chronological order of this workout
			"day_of_week": 1,
			"exercises": [
				{
					"exercise_id": 247,
					"sets": 4,
					"reps": 10,
					"duration_seconds": 0,
					"rest_duration_seconds": 90,
					"order_index": 1 // Required: execution order inside this specific session
				}
			]
		}
	]
}
```

**Response Schema:**

```json
// Returns the newly created FullWorkoutPlanDetailResponse structure
{
  "plan_id": 105,
  "title": "My Custom Hypertrophy Plan",
  "workouts": [ ... ]
  // (Full structure identical to [GET] /workout/workout-plans/{plan_id}/full)
}
```

**Step 2: Assign the Plan to the User**
**Endpoint:** `[POST] /workout/workout-plans/assign`

**Payload Schema:**

```json
{
	"trainee_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
	"trainer_id": "",
	"plan_id": 0,
	"is_trainer_provided": false,
	"is_active": true,
	"start_date": "2026-04-29T15:22:37.456Z",
	"end_date": "2026-04-29T15:22:37.456Z"
}
```

**Response Schema:**

```json
{
	"id": 55,
	"plan_id": 105,
	"trainee_id": "123e4567-e89b-12d3-a456-426614174000",
	"trainer_id": null,
	"status": "active",
	"start_date": "2026-04-29T00:00:00Z",
	"end_date": "2026-07-29T00:00:00Z",
	"created_at": "2026-04-29T10:00:00Z",
	"updated_at": null
}
```

## 8. Create Workout Session Page

**Description:**
A sub-view active while inside the "Create Workout Plan" flow. It acts as an isolated staging area to build an individual session (e.g., "Leg Day"). No direct database endpoints are hit here. All configurations are kept in frontend state and rolled into the `[POST] /workout/workout-plans/create-full` array payload when the master plan is finalized.

### Component A: Session Metadata

Input fields for `title`, `description`, `estimated_duration_minutes`, and `day_of_week`.

### Component B: List of Exercises

A visual list of exercises currently added to the session, exposing numerical inputs for `sets`, `reps` (or `duration_seconds`), and `rest_duration_seconds`.

### Component C: Form Action Buttons (Add Exercise & Save Session)

#### 1. Add Exercise Button

Redirects user to the "Add/Replace Exercise Page" (Exercise Search Interface). Selecting an exercise pushes the `exercise_id` back into the local session context array.

#### 2. Save Workout Button

Consolidates Component A and Component B data into a single session object and returns the user to the "Create Workout Plan Page", injecting this session into the plan's `workouts` array.

## 9. Add/Replace Exercise Page

**Description:**
A modal or dedicated screen acting as a global search directory for exercises.

### Component A: Search Bar with Filter

#### Description

Allows users to input query strings or select tags to narrow down exercise results. To load available tag filters, call the exercise tag endpoint.

#### Endpoint (Fetch Available Exercise Tags): `[GET] /workout/exer-tags`

**Payload Schema:**

```json
// No payload required
```

**Response Schema:**

```json
[
	{
		"id": 1,
		"name": "chest"
	},
	{
		"id": 2,
		"name": "shoulders"
	}
]
```

### Component B: Exercises Search Results

#### Description

Executes the search and populates a selectable list of exercises. When an exercise is clicked, its ID and foundational payload are passed back to the Create Session array.

#### Endpoint: `[GET] /workout/exercises`

**Payload Schema (Query Parameters):**
`?name=push&is_equipment_needed=false&exer_tags=chest&exer_tags=shoulders`

**Response Schema:**

```json
[
	{
		"id": 247,
		"name": "Push Up",
		"description": "A classic bodyweight exercise.",
		"instruction": "Keep your core tight.",
		"is_equipment_needed": false,
		"video_url": "https://example.com/pushup.mp4",
		"image_url": "https://example.com/pushup.jpg",
		"is_by_reps": true,
		"is_by_duration": false,
		"created_at": "2026-04-29T10:00:00Z"
	}
]
```

## 10. AI-Generate Workout Plan Page

**Description:**
A conversational, prompt-based interface where a trainee enters fitness goals and an AI (Gemini) builds a fully structured workout setup. Note that this endpoint _only generates_ the preview structure based on the `CreateFullWorkoutPlan` schema—it does not save it to the database yet.

To actually commit the AI-generated results, the frontend must pass the generated response directly into `[POST] /workout/workout-plans/create-full` and then assign it.

### Component A: AI Prompt Generation

#### Description

Sends a natural language prompt to the AI backend, which parses the user context and returns the structural blueprint for a new plan matching the `CreateFullWorkoutPlan` backend schema.

#### Endpoint: `[POST] /workout/workout-plans/ai-generate-full`

**Payload Schema:**

```json
{
	"prompt": "I want a 3 day per week routine focusing on calisthenics. I am a beginner with no equipment."
}
```

**Response Schema:**

```json
// Returns a payload identical to the 'CreateFullWorkoutPlan' schema structure.
{
	"title": "3-Day Beginner Calisthenics",
	"description": "A no-equipment fundamental bodyweight routine...",
	"duration_minutes": 135,
	"difficulty": "beginner",
	"days_per_week": 3,
	"ai_generated": true, // Automatically flagged true by the AI
	"is_preset": false,
	"is_equipment_needed": false,
	"tags": ["bodyweight", "beginner", "calisthenics"],
	"workouts": [
		{
			"title": "Day 1: Upper Body Basics",
			"description": "Introduction to push ups and holds.",
			"estimated_duration_minutes": 45,
			"order_index": 1,
			"day_of_week": 1,
			"exercises": [
				{
					"exercise_id": 247, // Built-in backend exercise ID retrieved by AI
					"sets": 3,
					"reps": 8,
					"duration_seconds": 0,
					"rest_duration_seconds": 60,
					"order_index": 1
				}
			]
		}
	]
}
```

### Component B: Generate with AI Button

#### Description

A call-to-action button that triggers the AI generation process using the prompt from Component A.

**Endpoint:** `[POST] /workout/workout-plans/ai-generate-full`

Once the button is clicked and the front-end receives the generated JSON response, it redirects the user directly to the **Create Workout Plan Page** (Page 7).

The generated JSON completely populates the local state of the Create Workout Plan Page. From there, the user enters the standard Create Workout Plan flow, where they can review, tweak, or add new exercises to the AI blueprint. When finalized, the user saves the plan to the database using the Create Workout Plan flow's standard `[POST] /workout/workout-plans/create-full` and assigning it via `[POST] /workout/workout-plans/assign`.
