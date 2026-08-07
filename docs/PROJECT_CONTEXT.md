# Project Context

FoodAI Ecosystem is a commercial nutrition and physical activity tracking product with computer vision and AI assistance.

## Core User Scenario

1. The user photographs food.
2. The system recognizes products and ingredients.
3. The system estimates portion size and mass.
4. The system calculates calories, proteins, fats, carbohydrates, and other nutrients.
5. The user confirms or corrects the result.
6. Confirmed data is saved to the diary.
7. The system analyzes the user's daily intake.

## Later Product Areas

- AI nutrition assistant.
- AI trainer.
- AI assistant for habits and wellbeing.
- Workouts.
- Goals.
- Progress charts.
- Personalization.
- Subscription.
- Mobile application.
- HealthKit and Health Connect integrations.
- Smart scales and wearable devices.
- B2B API.

## Safety Positioning

AI must be presented as an assistant, not as a doctor, licensed nutritionist, psychologist, or medical decision system.

AI must not:

- diagnose diseases or disorders;
- prescribe medication;
- replace a physician;
- independently make medical decisions.

Potentially dangerous situations require separate safety logic.

## Initial Roles

- `anonymous`: unauthenticated visitor.
- `user`: regular user with access only to own profile, photos, meals, diary, goals, and AI history.
- `support`: technical support with no default access to diary contents, food photos, AI conversations, or health profile.
- `content_manager`: manages product catalog, nutrients, references, and content.
- `admin`: manages system and users according to permissions.
- `superuser`: technical system access, not for daily operations.

